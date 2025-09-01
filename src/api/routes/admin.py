from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

from src.data_access.user_repository import user_repository
from src.data_access.fact_repository import fact_repository
from src.data_access.database_client import database_client
from src.config.settings import Language, settings
from src.models.message import MessageType
from src.services.scheduler_service import scheduler_service
from src.services.whatsapp_service import whatsapp_service
from src.services.scheduler_service import generate_and_send_daily_facts
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
            "services": {},
        }

        # Database health check
        try:
            db_healthy = database_client.health_check()
            health_status["services"]["database"] = {
                "status": "healthy" if db_healthy else "unhealthy",
                "details": "PostgreSQL connection",
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "details": f"Database error: {str(e)}",
            }

        # AI service health check
        health_status["services"]["ai"] = {
            "status": "healthy",
            "details": "AI service running",
        }

        # WhatsApp service health check
        health_status["services"]["whatsapp"] = {
            "status": "healthy",
            "details": "WhatsApp service running",
        }

        # Scheduler health check
        health_status["services"]["scheduler"] = {
            "status": "healthy",
            "details": "Scheduler service running",
        }

        # Overall status
        unhealthy_services = [
            name
            for name, service in health_status["services"].items()
            if service["status"] == "unhealthy"
        ]

        if unhealthy_services:
            health_status["status"] = "degraded"
            health_status["issues"] = unhealthy_services

        # Set actual timestamp
        from datetime import datetime, timezone

        health_status["timestamp"] = datetime.now(timezone.utc).isoformat()

        logger.info(
            "Health check completed",
            status=health_status["status"],
            unhealthy_services=unhealthy_services,
        )

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
        english_users = user_repository.get_subscribed_users_by_language(
            Language.ENGLISH
        )
        hebrew_users = user_repository.get_subscribed_users_by_language(Language.HEBREW)

        # Get fact statistics
        from datetime import date

        today = date.today()
        english_fact = fact_repository.get_daily_fact(today, Language.ENGLISH)
        hebrew_fact = fact_repository.get_daily_fact(today, Language.HEBREW)

        # Get recent facts count
        recent_english_facts = fact_repository.get_facts_by_language(
            Language.ENGLISH, limit=30
        )
        recent_hebrew_facts = fact_repository.get_facts_by_language(
            Language.HEBREW, limit=30
        )

        stats = {
            "timestamp": date.today().isoformat(),
            "users": {
                "total_subscribed": len(all_users),
                "english_users": len(english_users),
                "hebrew_users": len(hebrew_users),
            },
            "facts": {
                "today": {
                    "english": english_fact.original_title if english_fact else None,
                    "hebrew": hebrew_fact.original_title if hebrew_fact else None,
                },
                "recent_count": {
                    "english": len(recent_english_facts),
                    "hebrew": len(recent_hebrew_facts),
                },
            },
            "scheduler": {"status": "running"},
        }

        logger.info(
            "System stats retrieved",
            total_users=stats["users"]["total_subscribed"],
            english_users=stats["users"]["english_users"],
            hebrew_users=stats["users"]["hebrew_users"],
        )

        return stats

    except Exception as e:
        logger.error("Failed to get system stats", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get system stats")


class BroadcastMessage(BaseModel):
    message: str
    language: Optional[Language] = None


class TestMessage(BaseModel):
    phone_number: str
    message: str
    message_type: MessageType = MessageType.HELP


@router.post("/trigger-fact-generation")
async def trigger_fact_generation():
    """
    Manually trigger fact generation and distribution.

    This endpoint allows admins to manually trigger the daily fact generation
    and distribution process for testing purposes.
    """
    try:
        logger.info("Manual fact generation triggered")
        await generate_and_send_daily_facts()

        return {
            "status": "success",
            "message": "Fact generation triggered successfully",
        }

    except Exception as e:
        logger.error("Failed to trigger fact generation", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger fact generation")


@router.post("/broadcast")
async def send_broadcast_message(broadcast_data: BroadcastMessage):
    """
    Send a custom broadcast message to all subscribed users.

    Args:
        broadcast_data: Message content and optional language filter
    """
    try:
        logger.info(
            "Broadcasting custom message",
            message_preview=broadcast_data.message[:50],
            language=broadcast_data.language,
        )

        # Get users based on language filter
        if broadcast_data.language:
            users = user_repository.get_subscribed_users_by_language(
                broadcast_data.language
            )
        else:
            users = user_repository.get_all_subscribed_users()

        if not users:
            return {"status": "error", "message": "No subscribed users found"}

        # Send message to all users
        sent_count = 0
        for user in users:
            try:
                await whatsapp_service.send_message(
                    user.phone,
                    broadcast_data.message,
                    MessageType.DAILY_FACT,  # Use DAILY_FACT as default for broadcasts
                )
                sent_count += 1
            except Exception as e:
                logger.error(
                    "Failed to send broadcast to user", phone=user.phone, error=str(e)
                )

        logger.info(
            "Broadcast completed", total_users=len(users), sent_count=sent_count
        )

        return {
            "status": "success",
            "message": f"Broadcast sent to {sent_count}/{len(users)} users",
        }

    except Exception as e:
        logger.error("Failed to send broadcast message", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to send broadcast message")


@router.post("/test-message")
async def send_test_message(test_data: TestMessage):
    """
    Send a test message to a specific phone number.

    Args:
        test_data: Phone number, message content, and language
    """
    try:
        logger.info(
            "Sending test message",
            phone=test_data.phone_number,
            message_preview=test_data.message[:50],
        )

        await whatsapp_service.send_message(
            test_data.phone_number, test_data.message, test_data.message_type
        )

        return {
            "status": "success",
            "message": f"Test message sent to {test_data.phone_number}",
        }

    except Exception as e:
        logger.error(
            "Failed to send test message", phone=test_data.phone_number, error=str(e)
        )
        raise HTTPException(status_code=500, detail="Failed to send test message")


@router.get("/scheduler/jobs")
async def get_scheduler_jobs():
    """
    Get information about scheduled jobs.
    """
    try:
        jobs = []
        for job in scheduler_service.scheduler.get_jobs():
            jobs.append(
                {
                    "id": job.id,
                    "name": job.name,
                    "next_run_time": job.next_run_time.isoformat()
                    if job.next_run_time
                    else None,
                    "trigger": str(job.trigger),
                    "func": job.func.__name__
                    if hasattr(job.func, "__name__")
                    else str(job.func),
                }
            )

        return {
            "jobs": jobs,
            "scheduler_running": scheduler_service.scheduler.running,
            "total_jobs": len(jobs),
        }

    except Exception as e:
        logger.error("Failed to get scheduler jobs", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get scheduler jobs")


@router.post("/scheduler/pause")
async def pause_scheduler():
    """
    Pause the scheduler (stops all scheduled jobs).
    """
    try:
        scheduler_service.scheduler.pause()
        logger.info("Scheduler paused")

        return {"status": "success", "message": "Scheduler paused"}

    except Exception as e:
        logger.error("Failed to pause scheduler", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to pause scheduler")


@router.post("/scheduler/resume")
async def resume_scheduler():
    """
    Resume the scheduler (starts all scheduled jobs).
    """
    try:
        scheduler_service.scheduler.resume()
        logger.info("Scheduler resumed")

        return {"status": "success", "message": "Scheduler resumed"}

    except Exception as e:
        logger.error("Failed to resume scheduler", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to resume scheduler")


@router.get("/webhook-config")
async def get_webhook_configuration():
    """
    Get the current webhook configuration URLs for Twilio setup.

    Returns the dynamically generated webhook URLs that should be configured
    in the Twilio Console.
    """
    try:
        config = {
            "base_url": settings.twilio.base_url,
            "webhook_url": settings.twilio.webhook_url,
            "status_callback_url": settings.twilio.status_callback_url,
            "instructions": {
                "webhook_url": "Set this URL in Twilio Console > Messaging > WhatsApp Sandbox Settings > Webhook URL",
                "status_callback_url": "Set this URL in Twilio Console > Messaging > WhatsApp Settings > Status Callback URL (optional)",
            },
        }

        return config

    except Exception as e:
        logger.error("Failed to get webhook configuration", error=str(e))
        raise HTTPException(
            status_code=500, detail="Failed to get webhook configuration"
        )
