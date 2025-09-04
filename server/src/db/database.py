import json
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List, Dict, AsyncGenerator
from abc import ABC, abstractmethod
import aiosqlite
from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager, AbstractAsyncContextManager
from logging_config import get_logger

logger = get_logger(__name__)

# --- Abstract Base Classes ---


class AsyncDBTransaction(ABC):
    """Abstract base class for a transaction-bound database interface."""

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
    def transaction(self) -> AbstractAsyncContextManager[AsyncDBTransaction]:
        pass

    @abstractmethod
    async def executescript(self, script: str) -> None:
        pass


# --- PostgreSQL Implementation ---


class _PostgresTransaction(AsyncDBTransaction):
    def __init__(self, conn: AsyncConnection, db_instance: "PostgresDB"):
        self._conn = conn
        self._db_instance = db_instance

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))  # pyright: ignore[reportArgumentType]

    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))  # pyright: ignore[reportArgumentType]
            return await cur.fetchall()

    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))  # pyright: ignore[reportArgumentType]
            return await cur.fetchone()

    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))  # pyright: ignore[reportArgumentType]
            return await cur.fetchone()


class PostgresDB(AsyncDB):
    def __init__(self, dsn: str):
        self._dsn = dsn
        self._pool: Optional[AsyncConnectionPool] = None

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
            if isinstance(p, (dict, list)):
                processed.append(json.dumps(p))
            elif isinstance(p, UUID):
                processed.append(str(p))
            else:
                processed.append(p)
        return tuple(processed)

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))  # pyright: ignore[reportArgumentType]

    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))  # pyright: ignore[reportArgumentType]
                return await cur.fetchall()

    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
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

    async def executescript(self, script: str) -> None:
        await self.execute(script)

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[_PostgresTransaction, None]:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.transaction():
                yield _PostgresTransaction(conn, self)


# --- SQLite Implementation ---


class _SQLiteTransaction(AsyncDBTransaction):
    def __init__(self, conn: aiosqlite.Connection, db_instance: "SQLiteDB"):
        self._conn = conn
        self._db_instance = db_instance

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        await self._conn.execute(
            query.replace("%s", "?"), self._db_instance._process_params(params) or ()
        )

    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        async with self._conn.execute(
            query.replace("%s", "?"), self._db_instance._process_params(params) or ()
        ) as cursor:
            rows = await cursor.fetchall()
            return self._db_instance._process_results([dict(row) for row in rows])

    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        async with self._conn.execute(
            query.replace("%s", "?"), self._db_instance._process_params(params) or ()
        ) as cursor:
            row = await cursor.fetchone()
            return self._db_instance._process_result(dict(row) if row else None)

    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        async with self._conn.execute(
            query.replace("%s", "?"), self._db_instance._process_params(params) or ()
        ) as cursor:
            row = await cursor.fetchone()
            await self._conn.commit()
            return self._db_instance._process_result(dict(row) if row else None)


class _SQLitePassthroughTransaction(AsyncDBTransaction):
    def __init__(self, db_instance: "SQLiteDB"):
        self._db_instance = db_instance

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        await self._db_instance.execute(query, params)

    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        return await self._db_instance.fetch_all(query, params)

    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        return await self._db_instance.fetch_one(query, params)

    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        return await self._db_instance.execute_and_fetch_one(query, params)


class SQLiteDB(AsyncDB):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None

    def _process_results(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        processed_rows = []
        for row in rows:
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, str):
                    try:
                        if (value.startswith("{") and value.endswith("}")) or (
                            value.startswith("[") and value.endswith("]")
                        ):
                            if json.loads(value) is not None:
                                processed_row[key] = json.loads(value)
                            else:
                                processed_row[key] = value
                        else:
                            processed_row[key] = value
                    except (json.JSONDecodeError, TypeError):
                        processed_row[key] = value
                elif key.endswith("_at") and isinstance(value, str):
                    try:
                        processed_row[key] = datetime.fromisoformat(
                            value.replace("Z", "+00:00")
                        )
                    except ValueError:
                        processed_row[key] = value
                else:
                    processed_row[key] = value
            processed_rows.append(processed_row)
        return processed_rows

    def _process_result(
        self, row: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        return self._process_results([row])[0]

    def _process_params(self, params: Optional[tuple]) -> Optional[tuple]:
        if not params:
            return None
        processed = []
        for p in params:
            if isinstance(p, (dict, list)):
                processed.append(json.dumps(p))
            elif isinstance(p, UUID):
                processed.append(str(p))
            elif isinstance(p, datetime):
                processed.append(p.isoformat())
            elif isinstance(p, bool):
                processed.append(1 if p else 0)
            else:
                processed.append(p)
        return tuple(processed)

    async def connect(self):
        if not self._conn:
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA foreign_keys = ON;")
            await self._conn.execute("PRAGMA journal_mode=WAL;")
            await self._conn.commit()

    async def disconnect(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        await self._conn.execute(
            query.replace("%s", "?"), self._process_params(params) or ()
        )
        await self._conn.commit()

    async def fetch_all(
        self, query: str, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        async with self._conn.execute(
            query.replace("%s", "?"), self._process_params(params) or ()
        ) as cursor:
            rows = await cursor.fetchall()
            return self._process_results([dict(row) for row in rows])

    async def fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        async with self._conn.execute(
            query.replace("%s", "?"), self._process_params(params) or ()
        ) as cursor:
            row = await cursor.fetchone()
            return self._process_result(dict(row) if row else None)

    async def execute_and_fetch_one(
        self, query: str, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        """Executes a query that writes data and returns the first result, with a commit."""
        if not self._conn:
            raise ConnectionError("Database is not connected")
        async with self._conn.execute(
            query.replace("%s", "?"), self._process_params(params) or ()
        ) as cursor:
            row = await cursor.fetchone()
            await self._conn.commit()
            return self._process_result(dict(row) if row else None)

    async def get_and_lock_pending_background_job(self) -> Optional[Dict[str, Any]]:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        async with self.transaction() as tx:
            job_row = await tx.fetch_one(
                "SELECT id FROM \"BackgroundJob\" WHERE status = 'pending' ORDER BY created_at LIMIT 1"
            )
            if not job_row:
                return None
            job_id = job_row["id"]
            await tx.execute(
                "UPDATE \"BackgroundJob\" SET status = 'in_progress', updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now') WHERE id = %s",
                (job_id,),
            )
            return await tx.fetch_one(
                'SELECT * FROM "BackgroundJob" WHERE id = %s', (job_id,)
            )

    async def executescript(self, script: str) -> None:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        await self._conn.executescript(script)
        await self._conn.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncDBTransaction, None]:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        yield _SQLitePassthroughTransaction(self)
