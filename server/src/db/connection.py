import os
from typing import Optional
import asyncio

from db.database import AsyncDB, PostgresDB
from db.migration_runner import apply_migrations
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

    db_type = os.getenv("DATABASE_TYPE", "postgres").lower()
    if db_type != "postgres":
        raise ValueError(f"Unsupported DATABASE_TYPE: {db_type}. Only 'postgres' is supported.")

    logger.info(f"Initializing database of type: {db_type}")

    db_url = os.environ.get(
        "DATABASE_URL", "postgresql://user:password@localhost:5432/lorecard"
    )
    db = PostgresDB(db_url)

    # Retry loop to wait for the PostgreSQL container to be ready
    max_retries = 10
    for i in range(max_retries):
        try:
            await db.connect()
            break
        except Exception as e:
            if i < max_retries - 1:
                logger.warning(f"Database connection failed, retrying in 1 second... ({i+1}/{max_retries})")
                await asyncio.sleep(1)
            else:
                logger.error("Database connection failed after multiple retries.")
                raise e

    await apply_migrations(db)


async def close_database():
    """Closes the global database connection."""
    global db
    if db:
        await db.disconnect()
        db = None
