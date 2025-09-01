from datetime import date as DateType
from typing import Optional, List
from sqlmodel import select
from sqlalchemy import desc

from src.models.fact import DailyFact, DailyFactCreate
from src.data_access.database_client import database_client
from src.utils.logger import get_logger

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
    
    def get_daily_hebrew_fact(self, fact_date: DateType) -> Optional[DailyFact]:
        """Get daily Hebrew fact for a specific date."""
        try:
            with database_client.get_session() as session:
                statement = select(DailyFact).where(
                    DailyFact.date == fact_date,
                    DailyFact.language == "he"
                )
                fact = session.exec(statement).first()
                
                if fact:
                    logger.debug("Daily Hebrew fact found", date=fact_date)
                else:
                    logger.debug("Daily Hebrew fact not found", date=fact_date)
                
                return fact
                
        except Exception as e:
            logger.error("Failed to get daily Hebrew fact", 
                        date=fact_date, 
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
    
    def get_recent_hebrew_facts(self, limit: int = 10) -> List[DailyFact]:
        """Get recent daily Hebrew facts."""
        try:
            with database_client.get_session() as session:
                statement = (
                    select(DailyFact)
                    .where(DailyFact.language == "he")
                    .order_by(desc(DailyFact.date))
                    .limit(limit)
                )
                facts = session.exec(statement).all()
                
                logger.debug("Retrieved recent Hebrew facts", 
                           count=len(facts), 
                           limit=limit)
                return facts
                
        except Exception as e:
            logger.error("Failed to get recent Hebrew facts", 
                        error=str(e))
            raise
    
    def hebrew_fact_exists(self, fact_date: DateType) -> bool:
        """Check if a daily Hebrew fact exists for the given date."""
        try:
            with database_client.get_session() as session:
                statement = select(DailyFact).where(
                    DailyFact.date == fact_date,
                    DailyFact.language == "he"
                )
                fact = session.exec(statement).first()
                
                exists = fact is not None
                logger.debug("Hebrew fact existence check", 
                           date=fact_date, 
                           exists=exists)
                
                return exists
                
        except Exception as e:
            logger.error("Failed to check Hebrew fact existence", 
                        date=fact_date, 
                        error=str(e))
            raise
    
    def get_latest_hebrew_fact(self) -> Optional[DailyFact]:
        """Get the most recent daily Hebrew fact."""
        try:
            with database_client.get_session() as session:
                statement = (
                    select(DailyFact)
                    .where(DailyFact.language == "he")
                    .order_by(desc(DailyFact.date))
                    .limit(1)
                )
                fact = session.exec(statement).first()
                
                if fact:
                    logger.debug("Latest Hebrew fact found", date=fact.date)
                else:
                    logger.debug("No Hebrew facts found")
                
                return fact
                
        except Exception as e:
            logger.error("Failed to get latest Hebrew fact", error=str(e))
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