from datetime import date as DateType
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

from src.config.settings import settings, Language
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
    Main job function to generate daily facts and send to all users.
    This runs once per day and generates one fact per language.
    """
    logger.info("Starting daily fact generation and distribution")
    
    try:
        today = DateType.today()
        languages = [Language.ENGLISH, Language.HEBREW]
        
        # Step 1: Check if facts already exist for today
        existing_facts = {}
        for language in languages:
            existing_fact = fact_repository.get_daily_fact(today, language)
            if existing_fact:
                existing_facts[language] = existing_fact.summary
                logger.info("Using existing fact for language",
                          language=language,
                          date=today)
        
        # Step 2: Generate missing facts
        facts_to_send = {}
        for language in languages:
            if language in existing_facts:
                facts_to_send[language] = existing_facts[language]
            else:
                fact_content = await _generate_daily_fact_for_language(language, today)
                if fact_content:
                    facts_to_send[language] = fact_content
                else:
                    logger.error("Failed to generate fact for language", language=language)
        
        # Step 3: Get users grouped by language
        users_by_language = {}
        for language in languages:
            if language in facts_to_send:
                users = user_repository.get_subscribed_users_by_language(language)
                if users:
                    users_by_language[language] = users
                    logger.info("Users found for language",
                               language=language,
                               count=len(users))
                else:
                    logger.warning("No subscribed users found for language",
                                 language=language)
        
        # Step 4: Send facts to all users
        if users_by_language and facts_to_send:
            send_results = await whatsapp_service.broadcast_daily_facts(
                users_by_language, facts_to_send
            )
            
            # Log results
            total_sent = sum(send_results.values())
            total_users = sum(len(users) for users in users_by_language.values())
            
            logger.info("Daily fact distribution completed",
                       total_users=total_users,
                       total_sent=total_sent,
                       results_by_language=send_results)
        else:
            logger.warning("No facts to send or no users found")
        
    except Exception as e:
        logger.error("Failed to generate and send daily facts", error=str(e))
        raise


async def _generate_daily_fact_for_language(language: Language, fact_date: DateType) -> str:
    """
    Generate a daily fact for a specific language.
    
    Args:
        language: Language to generate fact for
        fact_date: Date for the fact
    
    Returns:
        Generated fact content or empty string if failed
    """
    try:
        logger.info("Generating daily fact",
                   language=language,
                   date=fact_date)
        
        # Get random Wikipedia article
        article_data = wikipedia_service.get_random_article(language)
        if not article_data:
            logger.error("Failed to fetch Wikipedia article", language=language)
            return ""
        
        # Generate AI summary
        fact_summary = ai_service.generate_daily_fact_summary(article_data)
        if not fact_summary:
            logger.error("Failed to generate AI summary",
                       language=language,
                       title=article_data.get("title", ""))
            return ""
        
        # Save to database
        fact_data = DailyFactCreate(
            date=fact_date,
            language=language,
            original_title=article_data["title"],
            original_url=article_data["url"],
            summary=fact_summary
        )
        
        fact_repository.create_daily_fact(fact_data)
        
        logger.info("Daily fact generated and saved successfully",
                   language=language,
                   date=fact_date,
                   title=article_data["title"])
        
        return fact_summary
        
    except Exception as e:
        logger.error("Failed to generate daily fact for language",
                    language=language,
                    date=fact_date,
                    error=str(e))
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
        
        logger.info("Weekly cleanup completed",
                   deleted_facts=deleted_facts,
                   cutoff_date=cutoff_date)
        
    except Exception as e:
        logger.error("Failed to cleanup old data", error=str(e))


class SchedulerService:
    """Service for managing scheduled tasks with APScheduler."""
    
    def __init__(self):
        """Initialize the scheduler with database job store."""
        # Configure job store to use the same database
        jobstores = {
            'default': SQLAlchemyJobStore(
                url=settings.database.url,
                tablename='apscheduler_jobs'
            )
        }
        
        executors = {
            'default': AsyncIOExecutor()
        }
        
        job_defaults = {
            'coalesce': True,  # Run only one instance if multiple are due
            'max_instances': 1,  # Only one instance of each job at a time
            'misfire_grace_time': 900  # 15 minutes grace period for missed jobs
        }
        
        self.scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=settings.scheduler.timezone
        )
        
        logger.info("Scheduler service initialized",
                   timezone=settings.scheduler.timezone)
    
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
                'cron',
                hour=settings.scheduler.fact_generation_hour,
                minute=settings.scheduler.fact_generation_minute,
                id='daily_facts_generation',
                name='Generate and send daily facts',
                replace_existing=True
            )
            
            logger.info("Daily fact generation job scheduled",
                       hour=settings.scheduler.fact_generation_hour,
                       minute=settings.scheduler.fact_generation_minute)
            
            # Schedule cleanup job (runs weekly on Sunday at 2 AM)
            self.scheduler.add_job(
                cleanup_old_data,
                'cron',
                day_of_week='sun',
                hour=2,
                minute=0,
                id='weekly_cleanup',
                name='Weekly data cleanup',
                replace_existing=True
            )
            
            logger.info("Weekly cleanup job scheduled")
            
        except Exception as e:
            logger.error("Failed to schedule daily jobs", error=str(e))
            raise
    
    


# Global service instance
scheduler_service = SchedulerService()