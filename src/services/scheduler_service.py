from datetime import date as DateType
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from src.config.settings import settings
from src.services.wikipedia_service import wikipedia_service
from src.services.ai_service import ai_service
from src.services.whatsapp_service import whatsapp_service
from src.data_access.user_repository import user_repository
from src.data_access.fact_repository import fact_repository
from src.models.fact import DailyFactCreate
from src.utils.logger import get_logger

logger = get_logger(__name__)


async def generate_and_send_daily_facts():
    """
    Main job function to generate Hebrew daily facts and send to all users.
    This runs once per day and generates one Hebrew fact.
    """
    logger.info("Starting Hebrew daily fact generation and distribution")

    try:
        today = DateType.today()

        # Step 1: Check if Hebrew fact already exists for today
        existing_fact = fact_repository.get_daily_hebrew_fact(today)
        if existing_fact:
            fact_content = existing_fact.summary
            logger.info("Using existing Hebrew fact", date=today)
        else:
            # Step 2: Generate new Hebrew fact
            fact_content = await _generate_hebrew_daily_fact(today)
            if not fact_content:
                logger.error("Failed to generate Hebrew fact")
                return

        # Step 3: Get all subscribed Hebrew users
        users = user_repository.get_all_subscribed_users_hebrew()
        if not users:
            logger.warning("No subscribed Hebrew users found")
            return

        logger.info("Hebrew users found", count=len(users))

        # Step 4: Send facts to all Hebrew users
        send_results = await whatsapp_service.broadcast_daily_facts_hebrew(
            users, fact_content
        )

        logger.info(
            "Hebrew daily fact distribution completed",
            total_users=len(users),
            total_sent=send_results,
        )

    except Exception as e:
        logger.error("Failed to generate and send Hebrew daily facts", error=str(e))
        raise


async def _generate_hebrew_daily_fact(fact_date: DateType) -> str:
    """
    Generate a Hebrew daily fact.

    Args:
        fact_date: Date for the fact

    Returns:
        Generated fact content or empty string if failed
    """
    try:
        logger.info("Generating Hebrew daily fact", date=fact_date)

        # Get random Hebrew Wikipedia article
        article_data = wikipedia_service.get_random_hebrew_article()
        if not article_data:
            logger.error("Failed to fetch Hebrew Wikipedia article")
            return ""

        # Generate Hebrew AI summary
        fact_summary = ai_service.generate_hebrew_daily_fact(article_data)
        if not fact_summary:
            logger.error(
                "Failed to generate Hebrew AI summary",
                title=article_data.get("title", ""),
            )
            return ""

        # Save to database
        fact_data = DailyFactCreate(
            date=fact_date,
            original_title=article_data["title"],
            original_url=article_data["url"],
            summary=fact_summary,
        )

        fact_repository.create_daily_fact(fact_data)

        logger.info(
            "Hebrew daily fact generated and saved successfully",
            date=fact_date,
            title=article_data["title"],
        )

        return fact_summary

    except Exception as e:
        logger.error(
            "Failed to generate Hebrew daily fact",
            date=fact_date,
            error=str(e),
        )
        return ""


async def cleanup_old_data():
    """Clean up old facts and logs to keep database size manageable."""
    try:
        logger.info("Starting weekly data cleanup")

        # Keep facts for last 30 days only
        cutoff_date = DateType.today().replace(day=1)  # First day of current month
        if cutoff_date.month > 1:
            cutoff_date = cutoff_date.replace(month=cutoff_date.month - 1)
        else:
            cutoff_date = cutoff_date.replace(year=cutoff_date.year - 1, month=12)

        # Delete old facts
        deleted_facts = fact_repository.delete_old_facts(cutoff_date)

        logger.info(
            "Weekly cleanup completed",
            deleted_facts=deleted_facts,
            cutoff_date=cutoff_date,
        )

    except Exception as e:
        logger.error("Failed to cleanup old data", error=str(e))


class SchedulerService:
    """Service for managing scheduled tasks with APScheduler."""

    def __init__(self):
        """Initialize the scheduler with database job store."""
        # Configure job store to use the same database
        jobstores = {
            "default": SQLAlchemyJobStore(
                url=settings.database.url, tablename="apscheduler_jobs"
            )
        }

        executors = {"default": AsyncIOExecutor()}

        job_defaults = {
            "coalesce": True,  # Run only one instance if multiple are due
            "max_instances": 1,  # Only one instance of each job at a time
            "misfire_grace_time": 900,  # 15 minutes grace period for missed jobs
        }

        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.scheduler.timezone,
        )

        logger.info(
            "Scheduler service initialized", timezone=settings.scheduler.timezone
        )

    def start(self):
        """Start the scheduler."""
        try:
            self.scheduler.start()
            self._schedule_daily_jobs()
            logger.info("Scheduler started successfully")
        except Exception as e:
            logger.error("Failed to start scheduler", error=str(e))
            raise

    def shutdown(self):
        """Shutdown the scheduler."""
        try:
            self.scheduler.shutdown(wait=True)
            logger.info("Scheduler shutdown successfully")
        except Exception as e:
            logger.error("Failed to shutdown scheduler", error=str(e))

    def _schedule_daily_jobs(self):
        """Schedule daily fact generation and sending jobs."""
        try:
            # Schedule daily fact generation job
            self.scheduler.add_job(
                generate_and_send_daily_facts,
                "cron",
                hour=settings.scheduler.fact_generation_hour,
                minute=settings.scheduler.fact_generation_minute,
                id="daily_facts_generation",
                name="Generate and send daily facts",
                replace_existing=True,
            )

            logger.info(
                "Daily fact generation job scheduled",
                hour=settings.scheduler.fact_generation_hour,
                minute=settings.scheduler.fact_generation_minute,
            )

            # Schedule cleanup job (runs weekly on Sunday at 2 AM)
            self.scheduler.add_job(
                cleanup_old_data,
                "cron",
                day_of_week="sun",
                hour=2,
                minute=0,
                id="weekly_cleanup",
                name="Weekly data cleanup",
                replace_existing=True,
            )

            logger.info("Weekly cleanup job scheduled")

        except Exception as e:
            logger.error("Failed to schedule daily jobs", error=str(e))
            raise


# Global service instance
scheduler_service = SchedulerService()
