import sys
from db.connection import init_db
from logging_config import setup_logging, get_logger
import asyncio

setup_logging()
logger = get_logger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

logger.info("Initializing database...")
asyncio.run(init_db())
logger.info("Database initialized.")
