import os
from typing import Optional

from db.database import AsyncDB, PostgresDB, SQLiteDB
from logging_config import get_logger

logger = get_logger(__name__)

db: Optional[AsyncDB] = None


async def get_db_connection() -> AsyncDB:
    """
    Returns the global database connection instance.
    Initializes the database connection if it doesn't exist.
    """
    global db
    if db is None:
        await init_database()

    if db is None:  # check again after potential initialization
        raise ConnectionError("Database could not be initialized.")
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

    db_type = os.getenv("DATABASE_TYPE", "postgres").lower()
    logger.info(f"Initializing database of type: {db_type}")

    if db_type == "postgres":
        db_url = os.environ.get(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/lorebook_creator"
        )
        db = PostgresDB(db_url)
        schema_path = "src/schema.sql"
    elif db_type == "sqlite":
        db_url = os.environ.get("DATABASE_URL", "lorebook_creator.db")
        db = SQLiteDB(db_url)
        schema_path = "src/schema.sqlite.sql"
    else:
        raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}")

    await db.connect()
    initialized = await db.is_initialized()
    if not initialized:
        logger.info("Database tables not found, creating schema.")
        await db.init_db(schema_path)
    else:
        logger.info("Database already initialized.")


async def close_database():
    """Closes the global database connection."""
    global db
    if db:
        await db.disconnect()
        db = None
