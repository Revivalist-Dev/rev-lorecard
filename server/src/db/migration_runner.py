import os
import re
from typing import List, Tuple
from db.migrations.data_migrations import DATA_MIGRATIONS
from logging_config import get_logger
from db.database import AsyncDB

logger = get_logger(__name__)

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "migrations")


async def _create_migrations_table(db: AsyncDB, db_type: str):
    """Ensures the schema_migrations table exists."""
    if db_type == "postgres":
        query = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version BIGINT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:  # sqlite
        query = """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            )
        """
    await db.execute(query)


async def get_current_version(db: AsyncDB, db_type: str) -> int:
    """Gets the latest applied migration version from the database."""
    await _create_migrations_table(db, db_type)
    query = "SELECT MAX(version) as version FROM schema_migrations"
    result = await db.fetch_one(query)
    return result["version"] if result and result["version"] is not None else 0


def get_available_migrations(db_type: str) -> List[Tuple[int, str, str]]:
    """Scans the migrations directory for migration files."""
    migrations = []
    file_suffix = ".sql" if db_type == "postgres" else ".sqlite.sql"
    for filename in sorted(os.listdir(MIGRATIONS_DIR)):
        if db_type == "postgres" and filename.endswith(".sqlite.sql"):
            continue
        if filename.endswith(file_suffix):
            match = re.match(r"(\d+)_.*", filename)
            if match:
                version = int(match.group(1))
                filepath = os.path.join(MIGRATIONS_DIR, filename)
                migrations.append((version, filename, filepath))
    return migrations


async def apply_migrations(db: AsyncDB, db_type: str):
    """Applies all pending schema and data migrations."""
    current_version = await get_current_version(db, db_type)
    available_migrations = get_available_migrations(db_type)

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

        # Run schema and data migration within a single transaction for atomicity
        async with db.transaction() as tx:
            # 1. Apply schema migration
            if db_type == "sqlite":
                await tx.executescript(script)
            else:
                await tx.execute(script)  # pyright: ignore[reportArgumentType]

            # 2. Check for and run corresponding data migration
            if version in DATA_MIGRATIONS:
                logger.info(f"Running data migration for version {version}...")
                data_migration_func = DATA_MIGRATIONS[version]
                await data_migration_func(tx)  # Pass the transaction object
                logger.info(f"Data migration for version {version} completed.")

            # 3. Record the migration version
            await tx.execute(
                "INSERT INTO schema_migrations (version) VALUES (%s)", (version,)
            )
        logger.info(f"Successfully applied migration {name}.")

    logger.info("All migrations applied successfully.")
