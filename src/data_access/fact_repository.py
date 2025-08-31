from datetime import date as DateType
from typing import Optional, List
from sqlmodel import select
from sqlalchemy import desc

from src.models.fact import DailyFact, DailyFactCreate
from src.data_access.database_client import database_client
from src.utils.logger import get_logger
from src.config.settings import Language

logger = get_logger(__name__)


class FactRepository:
    """Repository for daily facts data operations."""
    
    def create_daily_fact(self, fact_data: DailyFactCreate) -> DailyFact:
        """Create a new daily fact."""
        try:
            with database_client.get_session() as session:
                fact = DailyFact(**fact_data.model_dump())
                session.add(fact)
                session.commit()
                session.refresh(fact)
                
                logger.info("Daily fact created successfully", 
                          date=fact.date, 
                          language=fact.language, 
                          title=fact.original_title)
                return fact
                
        except Exception as e:
            logger.error("Failed to create daily fact", 
                        date=fact_data.date, 
                        language=fact_data.language, 
                        error=str(e))
            raise
    
    def get_daily_fact(self, fact_date: DateType, language: Language) -> Optional[DailyFact]:
        """Get daily fact for a specific date and language."""
        try:
            with database_client.get_session() as session:
                statement = select(DailyFact).where(
                    DailyFact.date == fact_date,
                    DailyFact.language == language
                )
                fact = session.exec(statement).first()
                
                if fact:
                    logger.debug("Daily fact found", date=fact_date, language=language)
                else:
                    logger.debug("Daily fact not found", date=fact_date, language=language)
                
                return fact
                
        except Exception as e:
            logger.error("Failed to get daily fact", 
                        date=fact_date, 
                        language=language, 
                        error=str(e))
            raise
    
    def get_facts_by_date(self, fact_date: DateType) -> List[DailyFact]:
        """Get all daily facts for a specific date (all languages)."""
        try:
            with database_client.get_session() as session:
                statement = select(DailyFact).where(DailyFact.date == fact_date)
                facts = session.exec(statement).all()
                
                logger.debug("Retrieved daily facts by date", date=fact_date, count=len(facts))
                return facts
                
        except Exception as e:
            logger.error("Failed to get facts by date", date=fact_date, error=str(e))
            raise
    
    def get_facts_by_language(self, language: Language, limit: int = 10) -> List[DailyFact]:
        """Get recent daily facts for a specific language."""
        try:
            with database_client.get_session() as session:
                statement = (
                    select(DailyFact)
                    .where(DailyFact.language == language)
                    .order_by(desc(DailyFact.date))
                    .limit(limit)
                )
                facts = session.exec(statement).all()
                
                logger.debug("Retrieved facts by language", 
                           language=language, 
                           count=len(facts), 
                           limit=limit)
                return facts
                
        except Exception as e:
            logger.error("Failed to get facts by language", 
                        language=language, 
                        error=str(e))
            raise
    
    def fact_exists(self, fact_date: DateType, language: Language) -> bool:
        """Check if a daily fact exists for the given date and language."""
        try:
            with database_client.get_session() as session:
                statement = select(DailyFact).where(
                    DailyFact.date == fact_date,
                    DailyFact.language == language
                )
                fact = session.exec(statement).first()
                
                exists = fact is not None
                logger.debug("Fact existence check", 
                           date=fact_date, 
                           language=language, 
                           exists=exists)
                
                return exists
                
        except Exception as e:
            logger.error("Failed to check fact existence", 
                        date=fact_date, 
                        language=language, 
                        error=str(e))
            raise
    
    def get_latest_fact_by_language(self, language: Language) -> Optional[DailyFact]:
        """Get the most recent daily fact for a specific language."""
        try:
            with database_client.get_session() as session:
                statement = (
                    select(DailyFact)
                    .where(DailyFact.language == language)
                    .order_by(desc(DailyFact.date))
                    .limit(1)
                )
                fact = session.exec(statement).first()
                
                if fact:
                    logger.debug("Latest fact found", language=language, date=fact.date)
                else:
                    logger.debug("No facts found", language=language)
                
                return fact
                
        except Exception as e:
            logger.error("Failed to get latest fact", language=language, error=str(e))
            raise
    
    def delete_old_facts(self, older_than_date: DateType) -> int:
        """Delete facts older than the specified date."""
        try:
            with database_client.get_session() as session:
                statement = select(DailyFact).where(DailyFact.date < older_than_date)
                old_facts = session.exec(statement).all()
                
                count = len(old_facts)
                for fact in old_facts:
                    session.delete(fact)
                
                session.commit()
                
                logger.info("Old facts deleted", count=count, older_than_date=older_than_date)
                return count
                
        except Exception as e:
            logger.error("Failed to delete old facts", 
                        older_than_date=older_than_date, 
                        error=str(e))
            raise


# Global repository instance
fact_repository = FactRepository()