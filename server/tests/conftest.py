import asyncio
import sys
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from psycopg_pool import AsyncConnectionPool
from litestar.testing import AsyncTestClient

from db.connection import close_pool, init_db, set_pool
from main import create_app

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:13") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def db_connection_pool(postgres_container: PostgresContainer):
    dsn = postgres_container.get_connection_url().replace("+psycopg2", "")
    pool = AsyncConnectionPool(conninfo=dsn, min_size=1, max_size=10)
    await pool.open()
    set_pool(pool)  # pyright: ignore[reportArgumentType]
    yield pool
    await close_pool()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(db_connection_pool: AsyncConnectionPool):
    await init_db()


@pytest_asyncio.fixture(scope="session")
async def client_test(db_connection_pool):
    app = create_app()
    async with AsyncTestClient(app) as client:
        yield client
