#!/usr/bin/env python3
"""
WikiBot - WhatsApp Wikipedia Facts Bot

A FastAPI application that sends daily Wikipedia facts to WhatsApp users
in English and Hebrew using AI summarization and cost-optimized distribution.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import all models to ensure they're registered with SQLModel metadata

from src.config.settings import settings
from src.api.routes import webhook, admin
from src.api.middleware import RequestLoggingMiddleware, SecurityHeadersMiddleware
from src.services.scheduler_service import scheduler_service
from src.data_access.database_client import database_client
from src.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events for the FastAPI application.
    """
    # Startup
    logger.info("Starting WikiBot application")
    
    try:
        # Initialize database connection
        logger.info("Initializing database connection")
        if not database_client.health_check():
            logger.error("Database connection failed during startup")
            raise RuntimeError("Database connection failed")
        
        # Start scheduler
        logger.info("Starting scheduler service")
        scheduler_service.start()
        
        logger.info("WikiBot application started successfully",
                   host=settings.server.host,
                   port=settings.server.port)
        
        yield
        
    except Exception as e:
        logger.error("Failed to start WikiBot application", error=str(e))
        raise
    finally:
        # Shutdown
        logger.info("Shutting down WikiBot application")
        
        try:
            # Stop scheduler
            logger.info("Stopping scheduler service")
            scheduler_service.shutdown()
            
            logger.info("WikiBot application shut down successfully")
            
        except Exception as e:
            logger.error("Error during application shutdown", error=str(e))


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Create FastAPI app with lifespan manager
    app = FastAPI(
        title="WikiBot - Wikipedia Facts Bot",
        description="A WhatsApp bot that sends daily Wikipedia facts in English and Hebrew",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env_id != "production" else None,
        redoc_url="/redoc" if settings.env_id != "production" else None
    )
    
    # Add middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(SecurityHeadersMiddleware)
    
    # Add CORS middleware for development
    if settings.env_id in ["local", "development"]:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    # Include routers
    app.include_router(webhook.router, tags=["Webhooks"])
    app.include_router(admin.router, tags=["Admin"])
    
    return app


# Create the app instance
app = create_app()


@app.get("/")
async def root():
    """Root endpoint with basic information."""
    return {
        "name": "WikiBot",
        "description": "Wikipedia Facts WhatsApp Bot",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.env_id.value
    }


@app.get("/health")
async def simple_health():
    """Simple health check endpoint."""
    try:
        db_healthy = database_client.health_check()
        
        return {
            "status": "healthy" if db_healthy else "unhealthy",
            "database": "connected" if db_healthy else "disconnected",
            "timestamp": "2024-01-01T00:00:00Z"  # Will be actual timestamp
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"  # Will be actual timestamp
        }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting WikiBot with uvicorn",
               host=settings.server.host,
               port=settings.server.port,
               reload=settings.server.reload,
               log_level=settings.server.log_level)
    
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload,
        log_level=settings.server.log_level
    )
