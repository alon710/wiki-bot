from datetime import datetime, timezone
from datetime import date as DateType
from typing import Optional
from sqlmodel import SQLModel, Field
from sqlalchemy import Index

from src.config.settings import Language


class DailyFact(SQLModel, table=True):
    """Model for daily Wikipedia facts."""
    
    __tablename__ = "daily_facts"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    date: DateType = Field(..., description="Date this fact is for", index=True)
    language: Language = Field(..., description="Language of the fact", index=True)
    original_title: str = Field(..., description="Original Wikipedia article title")
    original_url: str = Field(..., description="URL to the original Wikipedia article")
    summary: str = Field(..., description="AI-generated summary of the fact")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    
    __table_args__ = (
        Index('ix_daily_facts_date_language', 'date', 'language', unique=True),
    )


class DailyFactCreate(SQLModel):
    """Model for creating a new daily fact."""
    
    date: DateType = Field(..., description="Date this fact is for")
    language: Language = Field(..., description="Language of the fact")
    original_title: str = Field(..., description="Original Wikipedia article title")
    original_url: str = Field(..., description="URL to the original Wikipedia article")
    summary: str = Field(..., description="AI-generated summary of the fact")