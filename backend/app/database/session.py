import os
import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.config.settings import settings

logger = logging.getLogger("agrikural.database")

# Detect connection string
db_url = settings.DATABASE_URL

# In SQLite, ensure data directory exists
if "sqlite" in db_url:
    os.makedirs("./data", exist_ok=True)

try:
    engine = create_async_engine(
        db_url,
        echo=settings.SQL_ECHO,
        future=True,
        # Connection pooling settings for Postgres
        **({} if "sqlite" in db_url else {"pool_pre_ping": True, "pool_size": 10, "max_overflow": 20})
    )
except Exception as e:
    logger.warning(f"Failed to create engine with {db_url}: {e}. Falling back to SQLite.")
    db_url = "sqlite+aiosqlite:///./data/agrikural.db"
    engine = create_async_engine(db_url, echo=settings.SQL_ECHO, future=True)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
