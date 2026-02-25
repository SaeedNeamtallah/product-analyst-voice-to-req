"""
Database connection management with async SQLAlchemy.
Provides engine and session factory.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from backend.config import settings
import logging

logger = logging.getLogger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=300,
    pool_timeout=30,
    future=True,
)

# Create async session factory
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncSession:
    """
    Dependency function to get database session.
    Use with FastAPI Depends().

    Callers (routes/controllers) must explicitly ``await db.commit()``
    when they want to persist changes.  The session will auto-rollback
    on unhandled exceptions and always close when the request ends.
    """
    async with async_session_maker() as session:
        yield session


async def init_db():
    """Initialize database - create tables if they don't exist."""
    from backend.database.models import Base
    from sqlalchemy import text

    async def ensure_schema_compat(conn):
        column_exists = await conn.execute(text("""
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = 'projects'
              AND column_name = 'user_id'
            LIMIT 1
        """))
        if column_exists.scalar_one_or_none() is None:
            logger.warning("Legacy schema detected: adding projects.user_id column")
            await conn.execute(text("ALTER TABLE projects ADD COLUMN user_id INTEGER"))
            await conn.execute(text("CREATE INDEX IF NOT EXISTS ix_projects_user_id ON projects (user_id)"))

    startup_error = None
    try:
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            await ensure_schema_compat(conn)
            logger.info("Database initialized successfully")
            return
    except Exception as e:
        startup_error = e
        logger.warning(f"Initial database initialization attempt failed: {str(e)}")
        logger.info("Attempting fallback initialization...")
        try:
            async with engine.begin() as conn:
                # Try to create tables one by one or skip those that fail
                await conn.run_sync(Base.metadata.create_all)
                await ensure_schema_compat(conn)
                logger.info("Database tables initialized (some might have failed)")
                return
        except Exception as e2:
            logger.error(f"Failed to initialize database tables: {str(e2)}")
            startup_error = e2

    if startup_error is not None:
        raise RuntimeError("Database initialization failed") from startup_error


async def close_db():
    """Close database connections."""
    await engine.dispose()
    logger.info("Database connections closed")
