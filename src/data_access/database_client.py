from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlmodel import text
from typing import Optional, Generator
from contextlib import contextmanager

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseClient:
    """PostgreSQL database client using SQLModel."""

    _instance: Optional["DatabaseClient"] = None
    _engine = None
    _session_factory = None

    def __new__(cls) -> "DatabaseClient":
        """Singleton pattern for database client."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize database client."""
        if self._engine is None:
            self._initialize_database()

    def _initialize_database(self):
        """Initialize database engine and session factory."""
        try:
            # Fix postgres:// URLs to postgresql:// for SQLAlchemy 1.4+
            database_url = settings.database.url
            if database_url.startswith("postgres://"):
                database_url = database_url.replace("postgres://", "postgresql://", 1)

            self._engine = create_engine(
                database_url,
                echo=settings.database.echo,
                pool_size=settings.database.pool_size,
                max_overflow=settings.database.max_overflow,
            )

            self._session_factory = sessionmaker(
                autocommit=False, autoflush=False, bind=self._engine
            )

            logger.info(
                "Database initialized successfully",
                database_url=settings.database.url.split("@")[1]
                if "@" in settings.database.url
                else settings.database.url,
            )

        except Exception as e:
            logger.error("Failed to initialize database", error=str(e))
            raise

    @property
    def engine(self):
        """Get SQLAlchemy engine."""
        if self._engine is None:
            raise RuntimeError("Database not initialized")
        return self._engine

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with context manager."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")

        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            with self.get_session() as session:
                session.execute(text("SELECT 1"))  # Corrected line
            return True
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Global instance
database_client = DatabaseClient()
