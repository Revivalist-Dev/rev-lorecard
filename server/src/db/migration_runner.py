import os
import re
from typing import List, Tuple
from db.migrations.data_migrations import DATA_MIGRATIONS
from psycopg import sql
from logging_config import get_logger
from db.database import AsyncDB

logger = get_logger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


async def _create_migrations_table(db: AsyncDB):
    """Ensures the schema_migrations table exists for PostgreSQL."""
    logger.debug("Checking for 'schema_migrations' table existence.")
    if await db.table_exists("schema_migrations"):
        logger.debug("'schema_migrations' table already exists.")
        return

    logger.info("Attempting to create 'schema_migrations' table.")
    query = """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version BIGINT PRIMARY KEY,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """
    await db.execute(query)
    
    if not await db.table_exists("schema_migrations"):
        logger.critical(
            "CRITICAL MIGRATION FAILURE: The 'schema_migrations' table could not be created or persisted. "
            "This indicates a fundamental issue with DDL execution or transaction management in the database layer."
        )
    else:
        logger.info("'schema_migrations' table successfully created and persisted.")


async def get_current_version(db: AsyncDB) -> int:
    """Gets the latest applied migration version from the database."""
    await _create_migrations_table(db)
    query = "SELECT MAX(version) as version FROM schema_migrations"
    result = await db.fetch_one(query)
    return result["version"] if result and result["version"] is not None else 0


def get_available_migrations() -> List[Tuple[int, str, str]]:
    """Scans the migrations directory for PostgreSQL migration files."""
    migrations = []
    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if filename.endswith(".sql") and not filename.endswith(".sqlite.sql"):
            match = re.match(r"(\d+)_.*", filename)
            if match:
                version = int(match.group(1))
                filepath = os.path.join(MIGRATIONS_DIR, filename)
                migrations.append((version, filename, filepath))
    return migrations


async def apply_migrations(db: AsyncDB):
    """Applies all pending schema and data migrations for PostgreSQL."""
    current_version = await get_current_version(db)
    available_migrations = get_available_migrations()

    logger.info(f"Current DB version: {current_version}")

    pending_migrations = [m for m in available_migrations if m[0] > current_version]

    if not pending_migrations:
        logger.info("Database is up to date.")
        return

    logger.info(f"Found {len(pending_migrations)} pending migrations.")

    for version, name, path in pending_migrations:
        logger.info(f"Applying migration {name}...")
        with open(path, "r") as f:
            script = f.read()

        # 1. Apply schema migration (manually splitting script and executing outside transaction)
        # DDL statements often cause implicit commits, so we execute them separately.
        statements = [s.strip() for s in script.split(';') if s.strip()]
        for i, statement in enumerate(statements):
            logger.debug(f"Executing DDL statement {i+1}/{len(statements)} for {name}: {statement[:80]}...")
            await db.execute(statement)
            logger.debug(f"DDL statement {i+1}/{len(statements)} executed successfully.")

        # 2. Run data migration and record version within a transaction for atomicity
        async with db.transaction() as tx:
            # 2a. Check for and run corresponding data migration
            if version in DATA_MIGRATIONS:
                logger.info(f"Running data migration for version {version}...")
                data_migration_func = DATA_MIGRATIONS[version]
                await data_migration_func(tx)  # Pass the transaction object
                logger.info(f"Data migration for version {version} completed.")

            # 2b. Record the migration version (using %s placeholder for psycopg)
            await tx.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
            )
        logger.info(f"Successfully applied migration {name}.")

    logger.info("All migrations applied successfully.")
