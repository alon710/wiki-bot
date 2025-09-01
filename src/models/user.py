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
    last_message_at: Optional[datetime] = Field(default=None, description="Last message received from user (for session tracking)", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="User creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")
    
    def is_in_session_window(self) -> bool:
        """Check if user is within 24-hour session window for free-form messages."""
        if not self.last_message_at:
            return False
        
        time_diff = datetime.now(timezone.utc) - self.last_message_at
        return time_diff.total_seconds() < 24 * 60 * 60  # 24 hours in seconds


class UserCreate(SQLModel):
    """Model for creating a new user."""
    
    phone: str = Field(..., description="User's phone number in international format")
    language: Language = Field(default=Language.ENGLISH, description="User's preferred language")


class UserUpdate(SQLModel):
    """Model for updating user preferences."""
    
    language: Optional[Language] = Field(default=None, description="User's preferred language")
    subscribed: Optional[bool] = Field(default=None, description="Whether user is subscribed to daily facts")
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Update timestamp")