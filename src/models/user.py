from datetime import datetime, timezone
from typing import Optional
from sqlmodel import SQLModel, Field

from src.config.settings import Language


class User(SQLModel, table=True):
    """User model for WhatsApp bot users."""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    phone: str = Field(..., description="User's phone number in international format", unique=True, index=True)
    language: Language = Field(default=Language.ENGLISH, description="User's preferred language")
    subscribed: bool = Field(default=True, description="Whether user is subscribed to daily facts")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="User creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class UserCreate(SQLModel):
    """Model for creating a new user."""
    
    phone: str = Field(..., description="User's phone number in international format")
    language: Language = Field(default=Language.ENGLISH, description="User's preferred language")


class UserUpdate(SQLModel):
    """Model for updating user preferences."""
    
    language: Optional[Language] = Field(default=None, description="User's preferred language")
    subscribed: Optional[bool] = Field(default=None, description="Whether user is subscribed to daily facts")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Update timestamp")