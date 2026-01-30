"""
Database connection and management.

Supports multiple database backends:
- SQLite for local development
- PostgreSQL for production

Usage:
    from src.data.database import get_engine, get_session

    # Get a database session
    with get_session() as session:
        instruments = session.query(Instrument).all()
"""

import os 
from contextlib import contextmanager
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session 
from typing import Generator

from src.data.models import Base

# Database URL from environment variables with SQLite fallback
def get_database_url() -> str:
    """
    Get database connection URL.

    Priority:
    1. DATABASE_URL environment variable (production
)
    2. SQLite file in project directory (development)

    Examples:
        PostgreSQL: postgresql://user:password@host:5432/quantdb
        SQLite: sqlite:///./data/quant_data.db
    """

    return os.getenv(
        "DATABASE_URL",
        "sqlite:///./data/quant_data.db"
    )

# Global engine (created once, reused)
_engine = None 

def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy database engine.

    The engine manages the connection pool to the database.
    We create it once and reuse it.
    """
    global _engine

    if _engine is None:
        url = get_database_url()

        if url.startswith("sqlite"):
            # SQLite doesn't support connection pooling, so we create a new engine each time
            _engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                echo=True, # Set True to see SQL queries (debugging)
            )
        else:
            # PostgreSQL supports connection pooling
            _engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True, # verify connections are still valid before use
                echo=True, # Set True to see SQL queries (debugging)
            )

    return _engine

def init_database():
    """
    Initialize the database by creating all tables.

    Safe to call multiple times - only creates tables if they don't exist.
    """
    engine = get_engine()
    Base.metadata.create_all(engine)
    print(f"Database initialized: {get_database_url()}")

def drop_database():
    """
    Drop all tables from the database. USE WITH CAUTION!

    This is a destructive operation and should only be used for testing or schema changes.
    """
    engine = get_engine()
    Base.metadata.drop_all(engine)
    print(f"All tables dropped")

_SessionFactory = None 

def get_session_factory() -> Session:
    """ Get or create a session factory."""
    global _SessionFactory

    if _SessionFactory is None:
        _SessionFactory = sessionmaker(bind=get_engine())

    return _SessionFactory

@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    Get a database session with automatic cleanup.

    Usage:
        with get_session() as session:
            session.query(Instrument).all()
            session.add(new_instrument)
            # Automatically commits or rolls back the transaction

    This pattern ensures:
    - Connections are returned to the pool
    - Transactions are automatically committed or rolled back
    - No resource leaks or connection errors
    """
    factory = get_session_factory()
    session = factory()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()