import os
import json
from uuid import UUID
from typing import Optional, Union, Any

from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

import psycopg

pool: Optional[AsyncConnectionPool] = None


async def get_pool() -> AsyncConnectionPool:
    """Get the async connection pool."""
    global pool
    if pool is None:
        DATABASE_URL = os.environ.get(
            "DATABASE_URL", "postgresql://user:password@localhost:5432/lorebook_creator"
        )
        pool = AsyncConnectionPool(conninfo=DATABASE_URL, min_size=10, max_size=300)
        await pool.open()
    if pool is None:
        raise ConnectionError("Database pool could not be initialized")
    return pool


def set_pool(new_pool: AsyncConnectionPool):
    """Set the connection pool. Used for testing."""
    global pool
    pool = new_pool


async def close_pool():
    """Close the connection pool."""
    global pool
    if pool:
        await pool.close()
        pool = None


async def init_db(conn: Optional[psycopg.AsyncConnection] = None):
    """Initialize the database from the schema.sql file."""
    with open("src/schema.sql", "r") as f:
        schema = f.read()
    await execute_query(schema, conn=conn)


def _process_param(p: Any) -> Any:
    if isinstance(p, dict):
        return json.dumps(p)
    if isinstance(p, UUID):
        return str(p)
    if isinstance(p, (list, tuple)):
        return [_process_param(item) for item in p]
    return p


async def _execute_query(
    method: str,
    query: str,
    params: Optional[Union[tuple, list]] = None,
    conn: Optional[psycopg.AsyncConnection] = None,
) -> Any:
    """Helper to execute a query with optional parameters."""
    global pool
    current_pool = pool or await get_pool()
    assert current_pool is not None, "Database pool is not initialized"

    async def _execute(connection: psycopg.AsyncConnection) -> Any:
        processed_params = tuple(_process_param(p) for p in params) if params else ()
        async with connection.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, processed_params)  # pyright: ignore[reportArgumentType]

            if method == "execute":
                return

            db_method = getattr(cur, method)
            return await db_method()

    if conn:
        return await _execute(conn)

    async with current_pool.connection() as connection:
        return await _execute(connection)


async def execute_query(
    query: str,
    params: Optional[Union[tuple, list]] = None,
    conn: Optional[psycopg.AsyncConnection] = None,
) -> None:
    """Execute a query with optional parameters."""
    await _execute_query("execute", query, params, conn)


async def fetch_query(
    query: str,
    params: Optional[Union[tuple, list]] = None,
    conn: Optional[psycopg.AsyncConnection] = None,
) -> list[dict]:
    """Execute a fetch query with optional parameters."""
    return await _execute_query("fetchall", query, params, conn)


async def fetchrow_query(
    query: str,
    params: Optional[Union[tuple, list]] = None,
    conn: Optional[psycopg.AsyncConnection] = None,
) -> Optional[dict]:
    """Execute a fetchrow query with optional parameters."""
    return await _execute_query("fetchone", query, params, conn)
