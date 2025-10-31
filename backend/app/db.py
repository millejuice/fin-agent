"""
Database configuration and session management.
"""
from contextlib import contextmanager
from sqlmodel import SQLModel, create_engine, Session
from app.config import settings
from app.logger import get_logger

logger = get_logger("db")

# Create engine with proper configuration
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # Set to True for SQL query debugging
    pool_pre_ping=True,  # Verify connections before using
)

def init_db() -> None:
    """
    Initialize database - create all tables.
    Should be called on application startup.
    """
    try:
        from app import models  # Ensure models are imported for metadata
        
        SQLModel.metadata.create_all(engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

@contextmanager
def get_session_context():
    """
    Context manager for database sessions.
    Usage:
        with get_session_context() as session:
            # use session
    """
    with Session(engine) as session:
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

def get_session() -> Session:
    """
    Dependency function for FastAPI route handlers.
    Yields a database session and ensures cleanup.
    """
    with Session(engine) as session:
        try:
            yield session
        finally:
            session.close()
