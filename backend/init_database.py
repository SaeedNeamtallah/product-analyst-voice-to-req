"""
Database initialization script.
Creates database and tables with pgvector extension.
"""
import asyncio
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.database import init_db
from backend.database.models import User
from backend.config import settings
import bcrypt
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_database_if_not_exists():
    """Create the database if it doesn't exist."""
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    
    # Parse connection string to get credentials for default 'postgres' db
    # Example: postgresql+asyncpg://ragmind:ragmind123@localhost:5555/ragmind
    db_url = settings.database_url.replace("postgresql+asyncpg://", "")
    auth, rest = db_url.split("@")
    user, password = auth.split(":")
    host_port, db_name = rest.split("/")
    host = host_port.split(":")[0]
    port = host_port.split(":")[1] if ":" in host_port else "5432"
    
    try:
        # Connect to default 'postgres' database
        conn = psycopg2.connect(
            dbname='postgres',
            user=user,
            password=password,
            host=host,
            port=port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cur = conn.cursor()
        
        # Check if database exists
        cur.execute(f"SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{db_name}'")
        exists = cur.fetchone()
        
        if not exists:
            logger.info(f"Creating database {db_name}...")
            cur.execute(f"CREATE DATABASE {db_name}")
            logger.info(f"Database {db_name} created successfully")
        else:
            logger.info(f"Database {db_name} already exists")
            
        cur.close()
        conn.close()
    except Exception as e:
        logger.error(f"Error creating database: {str(e)}")
        # We continue anyway, maybe it exists but we couldn't check


async def create_default_user():
    """Create a default admin user if it doesn't exist."""
    from sqlalchemy import select
    from backend.database.connection import async_session_maker

    async with async_session_maker() as session:
        result = await session.execute(select(User).where(User.email == "admin@ragmind.com"))
        if result.scalar_one_or_none() is not None:
            logger.info("Default admin user already exists")
            return

        password_hash = bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user = User(
            name="Admin",
            email="admin@ragmind.com",
            password_hash=password_hash,
            role="admin"
        )
        session.add(user)
        await session.commit()
        logger.info("✅ Default admin user created (admin@ragmind.com / admin123)")


async def main():
    """Initialize database."""
    try:
        # Step 1: Create database if needed
        await create_database_if_not_exists()
        
        logger.info(f"Connecting to database: {settings.database_url.split('@')[1]}")
        
        # Step 2: Initialize tables and extensions
        await init_db()

        logger.info("✅ Database initialized successfully!")
        logger.info("Tables created:")
        logger.info("  - projects")
        logger.info("  - assets")
        logger.info("  - chunks (with vector embeddings)")
        logger.info("Extensions enabled:")
        logger.info("  - pgvector")

        # Step 3: Create default admin user if no users exist
        await create_default_user()
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {str(e)}")
        return 1
    
    finally:
        from backend.database import close_db
        await close_db()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
