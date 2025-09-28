"""
Database configuration and session management
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import logging
from typing import Generator

from .config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper()))
logger = logging.getLogger(__name__)

# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    echo=settings.is_development,  # Log SQL queries in development
    pool_recycle=300,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "check_same_thread": False,
    } if "sqlite" in settings.DATABASE_URL else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create base class for models
Base = declarative_base()

# Naming convention for constraints
convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

Base.metadata = MetaData(naming_convention=convention)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize database tables
    """
    try:
        # Import all models to ensure they are registered
        from database.models import user, hardware, cable, location, transaction, audit_log, settings

        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")

        # Initialize default settings
        try:
            from settings.services import get_settings_service
            settings_service = get_settings_service()
            settings_service.initialize_default_settings()
            logger.info("Default settings initialized")
        except Exception as e:
            logger.warning(f"Could not initialize default settings: {e}")

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def test_db_connection() -> bool:
    """
    Test database connection
    """
    try:
        from sqlalchemy import text
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


def get_db_connection():
    """
    Get raw database connection for executing raw SQL queries
    Returns SQLAlchemy connection object
    """
    return engine.connect()