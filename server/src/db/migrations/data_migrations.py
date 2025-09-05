import json
from db.common import CreateGlobalTemplate
from db.database import AsyncDBTransaction, PostgresDB, SQLiteDB
from logging_config import get_logger
import default_templates

logger = get_logger(__name__)


async def v3_override_default_templates(tx: AsyncDBTransaction) -> None:
    """
    Data migration for schema version 3.
    Creates or fully overwrites the default global templates with the latest versions.
    Also updates all existing projects to use these new default templates.
    """
    logger.info("Running data migration for v3: Overriding default templates...")

    # Define the default templates from the module
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
    if isinstance(tx, PostgresDB):
        for default in defaults:
            query = """
                INSERT INTO "GlobalTemplate" (id, name, content)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    content = EXCLUDED.content,
                    name = EXCLUDED.name,
                    updated_at = CURRENT_TIMESTAMP
            """
            # The 'name' is the same as 'id' for these defaults
            await tx.execute(query, (default.id, default.name, default.content))
    elif isinstance(tx, SQLiteDB):
        async with tx.transaction():
            for default in defaults:
                # Remove
                await tx.execute(
                    'DELETE FROM "GlobalTemplate" WHERE id = %s', (default.id,)
                )
                # Insert
                await tx.execute(
                    'INSERT INTO "GlobalTemplate" (id, name, content) VALUES (%s, %s, %s)',
                    (default.id, default.name, default.content),
                )

    logger.info(f"Ensured {len(defaults)} global templates are up-to-date.")

    # 2. Override templates in all existing Projects
    projects_to_update = await tx.fetch_all('SELECT id, templates FROM "Project"')

    updated_count = 0
    for project_row in projects_to_update:
        templates = project_row["templates"]
        # Handle case where templates might be a string (SQLite) or dict (Postgres)
        if isinstance(templates, str):
            templates = json.loads(templates)

        # Overwrite with new defaults
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


# This maps the version number to the function that should be run for it.
DATA_MIGRATIONS = {
    3: v3_override_default_templates,
}
