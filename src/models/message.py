from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum
from sqlmodel import SQLModel, Field, Column
from sqlalchemy import JSON


class MessageType(str, Enum):
    """Types of messages that can be sent."""
    
    WELCOME = "welcome"
    DAILY_FACT = "daily_fact"
    LANGUAGE_CHANGED = "language_changed"
    SUBSCRIPTION_CHANGED = "subscription_changed"
    HELP = "help"
    ERROR = "error"


class MessageStatus(str, Enum):
    """Status of a sent message."""
    
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class WhatsAppMessage(SQLModel):
    """Model for WhatsApp messages (request/response model)."""
    
    to: str = Field(..., description="Recipient phone number")
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(..., description="Type of message")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")


class WhatsAppWebhookMessage(SQLModel):
    """Model for incoming WhatsApp webhook messages."""
    
    from_: str = Field(..., alias="from", description="Sender phone number")
    body: str = Field(..., description="Message body/content")
    timestamp: datetime = Field(..., description="Message timestamp")
    message_id: Optional[str] = Field(default=None, description="WhatsApp message ID")
    
    model_config = {"populate_by_name": True}


class MessageLog(SQLModel, table=True):
    """Model for logging sent messages."""
    
    __tablename__ = "message_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    to: str = Field(..., description="Recipient phone number", index=True)
    content: str = Field(..., description="Message content")
    message_type: MessageType = Field(..., description="Type of message")
    status: MessageStatus = Field(default=MessageStatus.PENDING, description="Message status")
    external_id: Optional[str] = Field(default=None, description="External message ID from provider")
    message_metadata: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON), description="Additional metadata")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")