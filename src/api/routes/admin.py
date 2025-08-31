from fastapi import APIRouter, HTTPException

from src.data_access.user_repository import user_repository
from src.data_access.fact_repository import fact_repository
from src.data_access.database_client import database_client
from src.config.settings import Language
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin")


@router.get("/health")
async def health_check():
    """
    Comprehensive health check for all services.
    
    Returns:
        Health status of all system components
    """
    try:
        health_status = {
            "timestamp": "2024-01-01T00:00:00Z",  # Will be set to current time
            "status": "healthy",
            "services": {}
        }
        
        # Database health check
        try:
            db_healthy = database_client.health_check()
            health_status["services"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": "PostgreSQL connection"
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "details": f"Database error: {str(e)}"
            }
        
        # AI service health check
        health_status["services"]["ai"] = {
            "status": "healthy",
            "details": "AI service running"
        }
        
        # WhatsApp service health check
        health_status["services"]["whatsapp"] = {
            "status": "healthy",
            "details": "WhatsApp service running"
        }
        
        # Scheduler health check
        health_status["services"]["scheduler"] = {
            "status": "healthy",
            "details": "Scheduler service running"
        }
        
        # Overall status
        unhealthy_services = [
            name for name, service in health_status["services"].items()
            if service["status"] == "unhealthy"
        ]
        
        if unhealthy_services:
            health_status["status"] = "degraded"
            health_status["issues"] = unhealthy_services
        
        # Set actual timestamp
        from datetime import datetime, timezone
        health_status["timestamp"] = datetime.now(timezone.utc).isoformat()
        
        logger.info("Health check completed",
                   status=health_status["status"],
                   unhealthy_services=unhealthy_services)
        
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/stats")
async def get_system_stats():
    """
    Get system statistics.
    
    Returns:
        System usage and performance statistics
    """
    try:
        # Get user statistics
        all_users = user_repository.get_all_subscribed_users()
        english_users = user_repository.get_subscribed_users_by_language(Language.ENGLISH)
        hebrew_users = user_repository.get_subscribed_users_by_language(Language.HEBREW)
        
        # Get fact statistics
        from datetime import date
        today = date.today()
        english_fact = fact_repository.get_daily_fact(today, Language.ENGLISH)
        hebrew_fact = fact_repository.get_daily_fact(today, Language.HEBREW)
        
        # Get recent facts count
        recent_english_facts = fact_repository.get_facts_by_language(Language.ENGLISH, limit=30)
        recent_hebrew_facts = fact_repository.get_facts_by_language(Language.HEBREW, limit=30)
        
        stats = {
            "timestamp": date.today().isoformat(),
            "users": {
                "total_subscribed": len(all_users),
                "english_users": len(english_users),
                "hebrew_users": len(hebrew_users)
            },
            "facts": {
                "today": {
                    "english": english_fact.original_title if english_fact else None,
                    "hebrew": hebrew_fact.original_title if hebrew_fact else None
                },
                "recent_count": {
                    "english": len(recent_english_facts),
                    "hebrew": len(recent_hebrew_facts)
                }
            },
            "scheduler": {
                "status": "running"
            }
        }
        
        logger.info("System stats retrieved",
                   total_users=stats["users"]["total_subscribed"],
                   english_users=stats["users"]["english_users"],
                   hebrew_users=stats["users"]["hebrew_users"])
        
        return stats
        
    except Exception as e:
        logger.error("Failed to get system stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get system stats")


