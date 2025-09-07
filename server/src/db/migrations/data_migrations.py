import json
from sqlite3 import OperationalError as SQLiteOperationalError
from typing import Dict
from uuid import uuid4
from db.common import CreateGlobalTemplate
from db.database import AsyncDBTransaction
from logging_config import get_logger
import default_templates
from services.encryption import encrypt

logger = get_logger(__name__)


async def _upsert_global_template(
    template: CreateGlobalTemplate, tx: AsyncDBTransaction
) -> None:
    """
    A common helper function to insert a global template, or update it if it already exists.
    Handles both PostgreSQL and SQLite dialects.
    """
    try:
        # Attempt PostgreSQL's "INSERT ON CONFLICT" for an atomic upsert
        pg_query = """
            INSERT INTO "GlobalTemplate" (id, name, content)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO UPDATE SET
                content = EXCLUDED.content,
                name = EXCLUDED.name,
                updated_at = CURRENT_TIMESTAMP
        """
        await tx.execute(pg_query, (template.id, template.name, template.content))
    except (Exception, SQLiteOperationalError) as e:
        # If the above fails (e.g., SQLiteOperationalError on "ON CONFLICT"),
        # fall back to the DELETE then INSERT method for SQLite.
        if "syntax error" in str(
            e
        ):  # A simple check to ensure it's likely a syntax issue
            logger.debug("Postgres-style upsert failed, falling back to SQLite method.")
            await tx.execute(
                'DELETE FROM "GlobalTemplate" WHERE id = %s', (template.id,)
            )
            await tx.execute(
                'INSERT INTO "GlobalTemplate" (id, name, content) VALUES (%s, %s, %s)',
                (template.id, template.name, template.content),
            )
        else:
            # Re-raise any other unexpected errors
            raise e


async def v3_override_default_templates(tx: AsyncDBTransaction) -> None:
    """
    Data migration for schema version 3.
    Creates or fully overwrites the default global templates with the latest versions.
    Also updates all existing projects to use these new default templates.
    """
    logger.info("Running data migration for v3: Overriding default templates...")

    defaults = [
        CreateGlobalTemplate(
            id="selector-prompt",
            name="selector_prompt",
            content=default_templates.selector_prompt,
        ),
        CreateGlobalTemplate(
            id="search-params-prompt",
            name="search_params_prompt",
            content=default_templates.search_params_prompt,
        ),
        CreateGlobalTemplate(
            id="entry-creation-prompt",
            name="entry_creation_prompt",
            content=default_templates.entry_creation_prompt,
        ),
        CreateGlobalTemplate(
            id="lorebook-definition",
            name="lorebook_definition",
            content=default_templates.lorebook_definition,
        ),
    ]

    # 1. Create or Overwrite Global Templates
    for default in defaults:
        await _upsert_global_template(default, tx)

    logger.info(f"Ensured {len(defaults)} global templates are up-to-date.")

    # 2. Override templates in all existing Projects
    projects_to_update = await tx.fetch_all('SELECT id, templates FROM "Project"')

    updated_count = 0
    for project_row in projects_to_update:
        templates = project_row["templates"]
        if isinstance(templates, str):
            templates = json.loads(templates)

        templates["selector_generation"] = defaults[0].content
        templates["search_params_generation"] = defaults[1].content
        templates["entry_creation"] = defaults[2].content
        templates["lorebook_definition"] = defaults[3].content

        await tx.execute(
            'UPDATE "Project" SET templates = %s WHERE id = %s',
            (json.dumps(templates), project_row["id"]),
        )
        updated_count += 1

    if updated_count > 0:
        logger.info(
            f"Overrode templates for {updated_count} existing projects with new defaults."
        )
    else:
        logger.info("No existing projects found to update templates for.")

    logger.info("Data migration for v3 completed successfully.")


async def v5_override_selector_prompt(tx: AsyncDBTransaction) -> None:
    """
    Data migration for schema version 5.
    Overrides the 'selector-prompt' global template and updates all existing projects
    to use this new version for their 'selector_generation' template.
    """
    logger.info("Running data migration for v5: Overriding selector-prompt template...")

    selector_template = CreateGlobalTemplate(
        id="selector-prompt",
        name="selector_prompt",
        content=default_templates.selector_prompt,
    )

    # 1. Update the global template
    await _upsert_global_template(selector_template, tx)
    logger.info("Successfully updated the 'selector_prompt' global template.")

    # 2. Update all existing projects to use the new selector prompt
    logger.info("Now updating existing projects to use the new selector prompt...")
    projects_to_update = await tx.fetch_all('SELECT id, templates FROM "Project"')

    updated_count = 0
    for project_row in projects_to_update:
        templates = project_row["templates"]
        if isinstance(templates, str):
            templates = json.loads(templates)

        # Specifically update only the selector generation template
        templates["selector_generation"] = selector_template.content

        await tx.execute(
            'UPDATE "Project" SET templates = %s WHERE id = %s',
            (json.dumps(templates), project_row["id"]),
        )
        updated_count += 1

    if updated_count > 0:
        logger.info(
            f"Updated the selector prompt for {updated_count} existing projects."
        )
    else:
        logger.info("No existing projects found to update.")

    logger.info("Data migration for v5 completed successfully.")


async def v6_migrate_to_credentials(tx: AsyncDBTransaction) -> None:
    """
    Data migration for schema version 6.
    - Reads `ai_provider_config` from the old project table structure.
    - Creates a new `Credential` for each unique provider config.
    - Updates each project to point to its corresponding new `Credential`.
    - Finally, drops the old table (for SQLite).
    """
    logger.info(
        "Running data migration for v6: Migrating ai_provider_config to Credentials..."
    )

    try:
        # In SQLite, the old table is named 'Project_old_for_credentials'
        projects = await tx.fetch_all(
            'SELECT id, ai_provider_config FROM "Project_old_for_credentials"'
        )
    except (Exception, SQLiteOperationalError):
        # In PostgreSQL, the column still exists on the 'Project' table
        projects = await tx.fetch_all('SELECT id, ai_provider_config FROM "Project"')

    if not projects:
        logger.info("No existing projects to migrate.")
        return

    # A map to store unique provider configs and their new credential ID
    config_to_credential_id: Dict[str, str] = {}

    for project in projects:
        config_raw = project.get("ai_provider_config")
        if not config_raw:
            continue

        config = json.loads(config_raw) if isinstance(config_raw, str) else config_raw

        # Create a stable key for the config to find duplicates
        config_key = json.dumps(config, sort_keys=True)
        credential_id = config_to_credential_id.get(config_key)

        if not credential_id:
            # This is a new, unique config. Create a credential for it.
            provider = config.get("api_provider")
            model = config.get("model_name")

            # Prepare credential values (only api_key for now)
            values_to_encrypt = {}
            # For this one-time migration, we don't have stored keys.
            # We can leave it empty, and the user will have to re-enter them.
            # This is safer than trying to guess or use env vars.

            encrypted_values = encrypt(json.dumps(values_to_encrypt))
            new_credential_id = uuid4()
            credential_name = f"Migrated - {provider} - {model}"

            await tx.execute(
                'INSERT INTO "Credential" (id, name, provider_type, "values") VALUES (%s, %s, %s, %s)',
                (new_credential_id, credential_name, provider, encrypted_values),
            )
            credential_id = str(new_credential_id)
            config_to_credential_id[config_key] = credential_id
            logger.info(f"Created new credential '{credential_name}' for migration.")

        # Update the project with the new structure
        await tx.execute(
            """
            UPDATE "Project"
            SET credential_id = %s, model_name = %s, model_parameters = %s
            WHERE id = %s
            """,
            (
                credential_id,
                config.get("model_name"),
                json.dumps(config.get("model_parameters", {})),
                project["id"],
            ),
        )
        logger.info(f"Migrated project {project['id']} to use new credential.")

    # For SQLite, we must now drop the old table
    try:
        await tx.execute("DROP TABLE IF EXISTS Project_old_for_credentials")
        logger.info("Dropped old project table for SQLite.")
    except (Exception, SQLiteOperationalError):
        pass  # This will fail on PostgreSQL, which is expected

    logger.info("Data migration for v6 completed successfully.")


# This maps the version number to the function that should be run for it.
DATA_MIGRATIONS = {
    3: v3_override_default_templates,
    5: v5_override_selector_prompt,
    6: v6_migrate_to_credentials,
}
