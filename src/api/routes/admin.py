from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from src.services.scheduler_service import scheduler_service
from src.services.wikipedia_service import wikipedia_service
from src.services.ai_service import ai_service
from src.services.whatsapp_service import whatsapp_service
from src.data_access.user_repository import user_repository
from src.data_access.fact_repository import fact_repository
from sqlmodel import SQLModel
from src.data_access.database_client import database_client
# Import all models to ensure they're registered with SQLModel metadata
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
        try:
            ai_healthy = ai_service.test_connection()
            health_status["services"]["ai"] = {
                "status": "healthy" if ai_healthy else "unhealthy",
                "details": "OpenAI API connection"
            }
        except Exception as e:
            health_status["services"]["ai"] = {
                "status": "unhealthy",
                "details": f"AI service error: {str(e)}"
            }
        
        # WhatsApp service health check
        try:
            whatsapp_healthy = await whatsapp_service.test_connection()
            health_status["services"]["whatsapp"] = {
                "status": "healthy" if whatsapp_healthy else "unhealthy",
                "details": "Twilio WhatsApp API connection"
            }
        except Exception as e:
            health_status["services"]["whatsapp"] = {
                "status": "unhealthy",
                "details": f"WhatsApp service error: {str(e)}"
            }
        
        # Scheduler health check
        try:
            scheduler_jobs = scheduler_service.list_jobs()
            health_status["services"]["scheduler"] = {
                "status": "healthy",
                "details": f"Scheduler running with {len(scheduler_jobs)} jobs"
            }
        except Exception as e:
            health_status["services"]["scheduler"] = {
                "status": "unhealthy",
                "details": f"Scheduler error: {str(e)}"
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
                "jobs": scheduler_service.list_jobs()
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


@router.post("/trigger-daily-facts")
async def trigger_daily_facts():
    """
    Manually trigger daily fact generation and distribution.
    
    Returns:
        Confirmation of job trigger
    """
    try:
        scheduler_service.trigger_daily_facts_now()
        
        logger.info("Daily facts job triggered manually")
        
        return JSONResponse({
            "status": "success",
            "message": "Daily facts job has been triggered"
        })
        
    except Exception as e:
        logger.error("Failed to trigger daily facts job", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger daily facts job")


@router.get("/jobs")
async def list_scheduled_jobs():
    """
    List all scheduled jobs.
    
    Returns:
        List of all scheduled jobs with their status
    """
    try:
        jobs = scheduler_service.list_jobs()
        
        logger.info("Listed scheduled jobs", count=len(jobs))
        
        return {"jobs": jobs}
        
    except Exception as e:
        logger.error("Failed to list scheduled jobs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to list scheduled jobs")


@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str):
    """
    Get status of a specific job.
    
    Args:
        job_id: ID of the job to check
    
    Returns:
        Job status information
    """
    try:
        job_status = scheduler_service.get_job_status(job_id)
        
        if "error" in job_status:
            raise HTTPException(status_code=404, detail=job_status["error"])
        
        logger.info("Job status retrieved", job_id=job_id)
        
        return job_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get job status", job_id=job_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get job status")


@router.post("/test-wikipedia/{language}")
async def test_wikipedia_service(language: str):
    """
    Test Wikipedia service by fetching a random article.
    
    Args:
        language: Language code (en or he)
    
    Returns:
        Random article data
    """
    try:
        if language == "en":
            lang = Language.ENGLISH
        elif language == "he":
            lang = Language.HEBREW
        else:
            raise HTTPException(status_code=400, detail="Invalid language code")
        
        article_data = wikipedia_service.get_random_article(lang)
        
        if not article_data:
            raise HTTPException(status_code=500, detail="Failed to fetch article")
        
        logger.info("Wikipedia service test completed",
                   language=language,
                   title=article_data.get("title", ""))
        
        return article_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Wikipedia service test failed", language=language, error=str(e))
        raise HTTPException(status_code=500, detail="Wikipedia service test failed")


@router.post("/test-ai")
async def test_ai_service():
    """
    Test AI service with a sample article.
    
    Returns:
        Generated fact summary
    """
    try:
        # Sample article data for testing
        test_article = {
            "title": "Artificial Intelligence",
            "summary": "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by humans and other animals.",
            "full_text": "Artificial intelligence (AI) is intelligence demonstrated by machines, as opposed to natural intelligence displayed by humans and other animals. Computer science defines AI research as the study of intelligent agents: any system that perceives its environment and takes actions that maximize its chance of achieving its goals.",
            "url": "https://en.wikipedia.org/wiki/Artificial_intelligence",
            "language": "en"
        }
        
        summary = ai_service.generate_daily_fact_summary(test_article)
        
        if not summary:
            raise HTTPException(status_code=500, detail="Failed to generate summary")
        
        logger.info("AI service test completed", summary_length=len(summary))
        
        return {
            "original_title": test_article["title"],
            "generated_summary": summary
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("AI service test failed", error=str(e))
        raise HTTPException(status_code=500, detail="AI service test failed")


@router.post("/create-tables")
async def create_database_tables():
    """
    Create database tables using SQLModel metadata (useful for initial setup).
    
    Returns:
        Confirmation of table creation
    """
    try:
        # Use SQLModel.metadata.create_all() to create all tables
        SQLModel.metadata.create_all(database_client.engine)
        
        logger.info("Database tables created successfully using SQLModel metadata")
        
        return JSONResponse({
            "status": "success",
            "message": "Database tables created successfully using SQLModel metadata"
        })
        
    except Exception as e:
        logger.error("Failed to create database tables", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to create database tables")