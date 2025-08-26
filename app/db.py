from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
from app.config import settings
from loguru import logger
import asyncio


def create_database_if_not_exists():
    """Create the database if it doesn't exist (PostgreSQL only)"""
    if "postgresql" in settings.database_url:
        try:
            # Extract connection details from URL
            # Format: postgresql://user:password@host:port/dbname
            parts = settings.database_url.replace("postgresql://", "").split("/")
            if len(parts) == 2:
                credentials_host = parts[0]  # user:password@host:port
                db_name = parts[1]  # dbname

                # Connect to default postgres database to create our database
                default_url = f"postgresql://{credentials_host}/postgres"
                temp_engine = create_engine(default_url)

                with temp_engine.connect() as conn:
                    # Check if database exists
                    result = conn.execute(
                        text("SELECT 1 FROM pg_database WHERE datname = :dbname"), {"dbname": db_name}
                    )
                    if not result.fetchone():
                        logger.info(f"Creating database: {db_name}")
                        # Close all connections to postgres database
                        conn.execute(text("COMMIT"))
                        conn.execute(text(f"CREATE DATABASE {db_name}"))
                        logger.info(f"Database '{db_name}' created successfully")
                    else:
                        logger.info(f"Database '{db_name}' already exists")

        except Exception as e:
            logger.warning(f"Could not create database automatically: {e}")
            logger.info("Please create the database manually or check PostgreSQL connection")


def create_tables():
    """Create all database tables"""
    try:
        # Try to create database first (PostgreSQL only)
        create_database_if_not_exists()

        # Create tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

    except Exception as e:
        logger.error(f"Failed to create tables: {e}")
        raise


# Create engine with appropriate configuration
if "sqlite" in settings.database_url:
    # SQLite configuration for local development
    engine = create_engine(
        settings.database_url,
        echo=settings.app_env == "dev",
        connect_args={"check_same_thread": False},  # Required for SQLite
    )
    logger.info("Using SQLite database")
else:
    # PostgreSQL configuration
    engine = create_engine(
        settings.database_url,
        echo=settings.app_env == "dev",
        pool_pre_ping=True,  # Verify connections before use
        pool_recycle=300,  # Recycle connections every 5 minutes
    )
    logger.info("Using PostgreSQL database")

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Database session dependency"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
