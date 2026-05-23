from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from backend.config import settings

# Configure connection pooling arguments based on the database driver
engine_kwargs = {}
if settings.DATABASE_URL.startswith("postgresql"):
    engine_kwargs = {
        "pool_size": settings.DB_POOL_SIZE,
        "max_overflow": settings.DB_MAX_OVERFLOW,
        "pool_recycle": 1800,  # recycle connections after 30 minutes
        "pool_pre_ping": True,  # check if connection is alive before issuing queries
    }
else:
    # SQLite fallback doesn't support pool_size and max_overflow in the same way
    engine_kwargs = {
        "pool_recycle": 1800,
        "pool_pre_ping": True,
    }

# Create async engine
engine = create_async_engine(settings.DATABASE_URL, **engine_kwargs)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

Base = declarative_base()

# Dependency to get db session in endpoints
async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
