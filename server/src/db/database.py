import json
from uuid import UUID
from datetime import datetime
from typing import Optional, Any, List, Dict, AsyncGenerator
from typing_extensions import LiteralString
from abc import ABC, abstractmethod
import aiosqlite
from psycopg import AsyncConnection, sql
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool
from contextlib import asynccontextmanager, AbstractAsyncContextManager
from logging_config import get_logger

logger = get_logger(__name__)

# --- Abstract Base Class ---


class AsyncDB(ABC):
    """Abstract base class for asynchronous database operations."""

    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def execute(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> None:
        pass

    @abstractmethod
    async def fetch_all(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_one(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    async def get_and_lock_pending_background_job(self) -> Optional[Dict[str, Any]]:
        pass

    @abstractmethod
    def transaction(self) -> AbstractAsyncContextManager["AsyncDBTransaction"]:
        """Provides a transactional context."""
        raise NotImplementedError

    @abstractmethod
    async def executescript(self, script: str) -> None:
        """Executes a multi-statement SQL script."""
        pass


class AsyncDBTransaction(ABC):
    """Abstract base class for a transaction-bound database interface."""

    @abstractmethod
    async def execute(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> None:
        pass

    @abstractmethod
    async def fetch_all(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def fetch_one(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        pass


# --- PostgreSQL Implementation ---


class _PostgresTransaction(AsyncDBTransaction):
    def __init__(self, conn: AsyncConnection, db_instance: "PostgresDB"):
        self._conn = conn
        self._db_instance = db_instance

    async def execute(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> None:
        async with self._conn.cursor() as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))

    async def fetch_all(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))
            return await cur.fetchall()

    async def fetch_one(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        async with self._conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql.SQL(query), self._db_instance._process_params(params))
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

    def _process_param(self, p: Any) -> Any:
        if isinstance(p, dict):
            return json.dumps(p)
        if isinstance(p, UUID):
            return str(p)
        return p

    def _process_params(self, params: Optional[tuple]) -> Optional[tuple]:
        return tuple(self._process_param(p) for p in params) if params else None

    async def execute(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> None:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))

    async def fetch_all(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))
                return await cur.fetchall()

    async def fetch_one(
        self, query: LiteralString, params: Optional[tuple] = None
    ) -> Optional[Dict[str, Any]]:
        if not self._pool:
            raise ConnectionError("Database pool is not initialized")
        async with self._pool.connection() as conn:
            async with conn.cursor(row_factory=dict_row) as cur:
                await cur.execute(sql.SQL(query), self._process_params(params))
                return await cur.fetchone()

    async def get_and_lock_pending_background_job(self) -> Optional[Dict[str, Any]]:
        query = """
            WITH oldest_pending AS (
                SELECT id
                FROM "BackgroundJob"
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 1
                FOR UPDATE SKIP LOCKED
            )
            UPDATE "BackgroundJob"
            SET status = 'in_progress', updated_at = NOW()
            WHERE id = (SELECT id FROM oldest_pending)
            RETURNING *;
        """
        return await self.fetch_one(query)

    async def executescript(self, script: str) -> None:
        # psycopg can execute multi-statement scripts with a single execute call
        await self.execute(script)  # pyright: ignore[reportArgumentType]

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


class SQLiteDB(AsyncDB):
    def __init__(self, db_path: str):
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._transaction_depth = 0

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

    async def connect(self):
        if not self._conn:
            self._conn = await aiosqlite.connect(self._db_path)
            self._conn.row_factory = aiosqlite.Row
            await self._conn.execute("PRAGMA foreign_keys = ON;")

    async def disconnect(self):
        if self._conn:
            await self._conn.close()
            self._conn = None

    def _process_param(self, p: Any) -> Any:
        if isinstance(p, dict) or isinstance(p, list):
            return json.dumps(p)
        if isinstance(p, UUID):
            return str(p)
        if isinstance(p, datetime):
            return p.isoformat()
        if isinstance(p, bool):
            return 1 if p else 0
        return p

    def _process_params(self, params: Optional[tuple]) -> Optional[tuple]:
        return tuple(self._process_param(p) for p in params) if params else None

    async def execute(self, query: str, params: Optional[tuple] = None) -> None:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        async with self._conn.execute(
            query.replace("%s", "?"), self._process_params(params) or ()
        ):
            pass
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
            await self._conn.commit()
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
            await self._conn.commit()
            return self._process_result(dict(row) if row else None)

    async def get_and_lock_pending_background_job(self) -> Optional[Dict[str, Any]]:
        if not self._conn:
            raise ConnectionError("Database is not connected")

        # This transaction locks the database, preventing race conditions for workers.
        async with self.transaction() as tx:
            select_query = """
                SELECT id FROM "BackgroundJob"
                WHERE status = 'pending'
                ORDER BY created_at
                LIMIT 1
            """
            job_row = await tx.fetch_one(select_query)

            if not job_row:
                return None

            job_id = job_row["id"]

            # SQLite >= 3.35.0 supports RETURNING on UPDATE
            update_query = """
                UPDATE "BackgroundJob"
                SET status = 'in_progress', updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = %s
                RETURNING *
            """
            return await tx.fetch_one(update_query, (job_id,))

    async def executescript(self, script: str) -> None:
        if not self._conn:
            raise ConnectionError("Database is not connected")
        async with self._conn.executescript(script):
            pass
        await self._conn.commit()

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[_SQLiteTransaction, None]:
        if not self._conn:
            raise ConnectionError("Database is not connected")

        if not self._conn.in_transaction:
            try:
                await self._conn.execute("BEGIN")
                yield _SQLiteTransaction(self._conn, self)
                await self._conn.commit()
            except Exception:
                await self._conn.rollback()
                raise
        else:
            # Already in a transaction, use a savepoint
            savepoint_name = f"savepoint_{self._transaction_depth}"
            try:
                self._transaction_depth += 1
                await self._conn.execute(f"SAVEPOINT {savepoint_name}")
                yield _SQLiteTransaction(self._conn, self)
                await self._conn.execute(f"RELEASE SAVEPOINT {savepoint_name}")
            except Exception:
                await self._conn.execute(f"ROLLBACK TO SAVEPOINT {savepoint_name}")
                raise
            finally:
                self._transaction_depth -= 1
