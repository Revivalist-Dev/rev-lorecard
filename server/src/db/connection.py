import os
from typing import Optional

from db.database import AsyncDB, PostgresDB, SQLiteDB
from db.migrations import apply_migrations
from logging_config import get_logger

logger = get_logger(__name__)

db: Optional[AsyncDB] = None


async def get_db_connection() -> AsyncDB:
    """
    Returns the global database connection instance.
    Raises an exception if the database has not been initialized.
    """
    if db is None:
        raise ConnectionError(
            "Database has not been initialized. Call init_database() first."
        )
    return db


def set_db_connection(new_db: AsyncDB):
    """Sets the global database connection instance, used for testing."""
    global db
    db = new_db


async def init_database():
    """Initializes the database based on environment variables."""
    global db
    if db:
        return

    db_type = os.getenv("DATABASE_TYPE", "sqlite").lower()
    logger.info(f"Initializing database of type: {db_type}")

    if db_type == "postgres":
        db_url = os.environ.get(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/lorebook_creator"
        )
        db = PostgresDB(db_url)
    elif db_type == "sqlite":
        db_url = os.environ.get("DATABASE_URL", "lorebook_creator.db")
        db = SQLiteDB(db_url)
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")

    await db.connect()
    await apply_migrations(db, db_type)


async def close_database():
    """Closes the global database connection."""
    global db
    if db:
        await db.disconnect()
        db = None
