from enum import Enum
import json
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List, Dict, AsyncGenerator
from abc import ABC, abstractmethod
from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager, AbstractAsyncContextManager
from logging_config import get_logger

logger = get_logger(__name__)


class DatabaseType(str, Enum):
    POSTGRES = "postgres"


# --- Abstract Base Classes ---


class AsyncDBTransaction(ABC):
    """Abstract base class for a transaction-bound database interface."""

    @abstractmethod
    def database_type(self) -> DatabaseType:
        pass

    @abstractmethod
    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        pass

    @abstractmethod
    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        pass



class AsyncDB(ABC):
    """Abstract base class for asynchronous database operations."""

    @abstractmethod
    def database_type(self) -> DatabaseType:
        pass

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        pass

    @abstractmethod
    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Executes a query that writes data and returns the first result."""
        pass

    @abstractmethod
    async def get_and_lock_pending_background_job(self) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def table_exists(self, table_name: str) -> bool:
        """Checks if a table exists in the database."""
        pass

    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager[AsyncDBTransaction]:
        pass



class PostgresDB(AsyncDB):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: Optional[AsyncConnectionPool] = None

    def database_type(self) -> DatabaseType:
        return DatabaseType.POSTGRES

    async def connect(self):
        if not self._pool:
            self._pool = AsyncConnectionPool(
                conninfo=self._dsn, min_size=10, max_size=300
            )
            await self._pool.open()

    async def disconnect(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    def _process_params(self, params: Optional[tuple]) -> Optional[tuple]:
        if not params:
            return None
        processed = []
        for p in params:
            if isinstance(p, (dict)):
                processed.append(json.dumps(p))
            elif isinstance(p, UUID):
                processed.append(str(p))
            else:
                processed.append(p)
        return tuple(processed)

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        logger.debug("Executing query: %s with params: %s", query, params)
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            # Set autocommit=True for non-transactional DDL execution
            await conn.set_autocommit(True)
            try:
                async with conn.cursor() as cur:
                    # Use raw query string for multi-statement scripts (migrations) when no parameters are passed
                    # Use sql.SQL for single-statement queries with parameters
                    await cur.execute(
                        sql.SQL(query),  # Always wrap query in sql.SQL for DDL/non-parameterized queries
                        self._process_params(params),
                    )  # pyright: ignore[reportArgumentType]
                await conn.commit() # Explicitly commit DDL changes
            finally:
                # The pool should handle resetting autocommit state upon return.
                pass

    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        logger.debug("Fetching all: %s with params: %s", query, params)
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))  # pyright: ignore[reportArgumentType]
                return await cur.fetchall()

    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        logger.debug("Fetching one: %s with params: %s", query, params)
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))  # pyright: ignore[reportArgumentType]
                return await cur.fetchone()

    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        return await self.fetch_one(query, params)

    async def get_and_lock_pending_background_job(self) -> Optional[Dict[str, Any]]:
        query = "WITH oldest_pending AS (SELECT id FROM \"BackgroundJob\" WHERE status = 'pending' ORDER BY created_at LIMIT 1 FOR UPDATE SKIP LOCKED) UPDATE \"BackgroundJob\" SET status = 'in_progress', updated_at = NOW() WHERE id = (SELECT id FROM oldest_pending) RETURNING *;"
        return await self.fetch_one(query)

    async def table_exists(self, table_name: str) -> bool:
        """Checks if a table exists in the database."""
        query = """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """
        result = await self.fetch_one(query, (table_name,))
        return result["exists"] if result else False

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncDBTransaction, None]:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        # psycopg's connection.transaction() handles nesting automatically!
        async with self._pool.connection() as conn:
            async with conn.transaction():
                # We need an object that has the execute/fetch methods.
                # We can create a simple wrapper around the connection.
                class PsycopgTransactionWrapper(AsyncDBTransaction):
                    def __init__(self, conn: AsyncConnection, db: PostgresDB):
                        self._conn = conn
                        self._db = db

                    def database_type(self) -> DatabaseType:
                        return self._db.database_type()

                    async def execute(
                        self, query: str, params: Optional[tuple] = None
                    ) -> None:
                        async with self._conn.cursor() as cur:
                            logger.debug("Executing transaction query: %s with params: %s", query, params)
                            # Use raw query string for multi-statement scripts (migrations) when no parameters are passed
                            # Use sql.SQL for single-statement queries with parameters
                            await cur.execute(
                                sql.SQL(query),  # Always wrap query in sql.SQL for DDL/non-parameterized queries
                                self._db._process_params(params),
                            )

                    async def fetch_all(
                        self, query: str, params: Optional[tuple] = None
                    ) -> List[Dict[str, Any]]:
                        async with self._conn.cursor(row_factory=dict_row) as cur:
                            logger.debug("Fetching all transaction query: %s with params: %s", query, params)
                            await cur.execute(
                                sql.SQL(query),  # pyright: ignore[reportArgumentType]
                                self._db._process_params(params),
                            )
                            return await cur.fetchall()

                    async def fetch_one(
                        self, query: str, params: Optional[tuple] = None
                    ) -> Optional[Dict[str, Any]]:
                        async with self._conn.cursor(row_factory=dict_row) as cur:
                            logger.debug("Fetching one transaction query: %s with params: %s", query, params)
                            await cur.execute(
                                sql.SQL(query),  # pyright: ignore[reportArgumentType]
                                self._db._process_params(params),
                            )
                            return await cur.fetchone()

                    async def execute_and_fetch_one(
                        self, query: str, params: Optional[tuple] = None
                    ) -> Optional[Dict[str, Any]]:
                        return await self.fetch_one(query, params)

                yield PsycopgTransactionWrapper(conn, self)


