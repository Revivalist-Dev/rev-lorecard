import asyncio
import sys
import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from litestar.testing import AsyncTestClient

from db.connection import set_db_connection, close_database
from db.database import PostgresDB, SQLiteDB, AsyncDB
from main import create_app

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session", params=["postgres", "sqlite"])
def db_type(request):
    return request.param


@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:13") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="session")
async def db(db_type: str, postgres_container: PostgresContainer, tmp_path_factory):
    if db_type == "postgres":
        dsn = postgres_container.get_connection_url().replace("+psycopg2", "")
        db_instance = PostgresDB(dsn)
    elif db_type == "sqlite":
        db_path = tmp_path_factory.mktemp("data") / "test.db"
        db_instance = SQLiteDB(str(db_path))
    else:
        raise ValueError(f"Unsupported db_type: {db_type}")

    await db_instance.connect()
    set_db_connection(db_instance)
    yield db_instance
    await close_database()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_database(db: AsyncDB):
    schema_path = (
        "src/schema.sql" if isinstance(db, PostgresDB) else "src/schema.sqlite.sql"
    )
    await db.init_db(schema_path)


@pytest_asyncio.fixture(scope="session")
async def client_test(db: AsyncDB):
    app = create_app()
    async with AsyncTestClient(app) as client:
        yield client
