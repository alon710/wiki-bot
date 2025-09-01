from sqlalchemy import create_engine
from sqlmodel import Session, text
from typing import Optional, Generator
from contextlib import contextmanager
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.exc import OperationalError, DisconnectionError

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
                # Connection pool settings for better reliability
                pool_pre_ping=True,  # Verify connections before use
                pool_recycle=3600,   # Recycle connections every hour
                # SSL and connection settings for PostgreSQL
                connect_args={
                    "sslmode": "prefer",
                    "connect_timeout": 10,
                    "application_name": "WikiBot"
                } if "postgresql" in database_url else {}
            )

            self._session_factory = lambda: Session(
                bind=self._engine, autocommit=False, autoflush=False
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
        except (OperationalError, DisconnectionError) as e:
            logger.warning("Database connection error, session will be rolled back", error=str(e))
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @contextmanager
    def get_session_no_commit(self) -> Generator[Session, None, None]:
        """Get database session with manual commit control."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")

        session = self._session_factory()
        try:
            yield session
            # No automatic commit - caller must handle commit/rollback
        except (OperationalError, DisconnectionError) as e:
            logger.warning("Database connection error, session will be rolled back", error=str(e))
            session.rollback()
            raise
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((OperationalError, DisconnectionError))
    )
    def execute_with_retry(self, operation):
        """Execute a database operation with automatic retry on connection failures."""
        with self.get_session() as session:
            return operation(session)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type((OperationalError, DisconnectionError))
    )
    def execute_with_retry_manual_commit(self, operation):
        """Execute a database operation with manual commit control and retry on connection failures."""
        with self.get_session_no_commit() as session:
            return operation(session)

    def health_check(self) -> bool:
        """Check if database connection is healthy."""
        try:
            def check_operation(session):
                session.exec(text("SELECT 1"))
                return True
                
            return self.execute_with_retry(check_operation)
        except Exception as e:
            logger.error("Database health check failed", error=str(e))
            return False


# Global instance
database_client = DatabaseClient()
