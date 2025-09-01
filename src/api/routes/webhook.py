from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, PlainTextResponse

from src.config.settings import settings
from src.models.message import WhatsAppWebhookMessage
from src.models.user import UserCreate, UserUpdate
from src.data_access.user_repository import user_repository
from src.services.whatsapp_service import whatsapp_service
from src.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    background_tasks: BackgroundTasks,
    From: str = Form(...),
    Body: str = Form(None),
    MessageSid: str = Form(...),
    To: str = Form(...)
):
    """
    Handle incoming WhatsApp webhook messages from Twilio.
    
    This endpoint receives messages from WhatsApp users and processes commands.
    Twilio sends webhook data as form-encoded data, not JSON.
    """
    try:
        # Log incoming webhook for debugging
        logger.info("Received WhatsApp webhook", 
                   from_phone=From, 
                   body=Body, 
                   message_sid=MessageSid)
        
        # Remove 'whatsapp:' prefix from phone numbers if present
        from_phone = From[9:] if From.startswith("whatsapp:") else From
        message_body = Body.strip() if Body else ""
        
        if not from_phone:
            logger.warning("Missing required phone field", from_phone=from_phone)
            return PlainTextResponse("", status_code=400)
        
        # Create webhook message model
        webhook_message = WhatsAppWebhookMessage(
            from_=from_phone,
            body=message_body,
            timestamp=datetime.now(timezone.utc),
            message_id=MessageSid
        )
        
        # Process message in background
        background_tasks.add_task(process_whatsapp_message, webhook_message)
        
        # Return empty response as expected by Twilio
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error("Failed to process WhatsApp webhook", error=str(e))
        return PlainTextResponse("", status_code=500)


async def process_whatsapp_message(message: WhatsAppWebhookMessage):
    """
    Process an individual WhatsApp message and handle commands.
    
    Args:
        message: The WhatsApp message to process
    """
    try:
        phone = message.from_
        body = message.body.lower().strip()
        
        logger.info("Processing WhatsApp message",
                   phone=phone,
                   body=body,
                   message_id=message.message_id)
        
        # Get or create user
        user = user_repository.get_user_by_phone(phone)
        
        if not user:
            # New user - create with default settings
            user_data = UserCreate(phone=phone)
            user = user_repository.create_user(user_data)
            
            # Send welcome message for new users
            await whatsapp_service.send_welcome_message(phone, user)
            
            logger.info("New user created and instructions sent", phone=phone, sandbox=settings.twilio.is_sandbox)
            return
        
        # Update last message timestamp for existing users
        user_repository.update_last_message(phone)
        
        # Process number responses or show main menu for any text message
        if body and body.strip().isdigit():
            await handle_number_response(phone, body.strip())
        else:
            # Any non-number message should get main menu
            await whatsapp_service.send_main_menu(phone, user)
        
    except Exception as e:
        logger.error("Failed to process WhatsApp message",
                    phone=message.from_,
                    body=message.body,
                    message_id=message.message_id,
                    error=str(e),
                    error_type=type(e).__name__,
                    error_module=getattr(e, '__module__', 'unknown'))


async def handle_number_response(phone: str, number: str):
    """
    Handle WhatsApp number responses.
    
    Args:
        phone: User phone number
        number: Number sent by user (1, 2, 3, etc.)
    """
    try:
        # Get fresh user data to avoid session issues
        user = user_repository.get_user_by_phone(phone)
        if not user:
            logger.warning("User not found for number processing", phone=phone)
            return
        
        # Main menu responses
        if number == "1":
            # Get Daily Fact - send help for now
            await whatsapp_service.send_help_message(phone)
            
        elif number == "2":
            # Toggle subscription
            await handle_subscription_toggle(phone, user)
            
        elif number == "3":
            # Help
            await whatsapp_service.send_help_message(phone)
            
        else:
            # Unknown number - show main menu
            await whatsapp_service.send_main_menu(phone, user)
        
        logger.info("Number response processed successfully",
                   phone=phone,
                   number=number)
        
    except Exception as e:
        logger.error("Failed to handle number response",
                    phone=phone,
                    number=number,
                    error=str(e),
                    error_type=type(e).__name__)


async def handle_subscription_toggle(phone: str, user):
    """Handle subscription toggle for user."""
    try:
        if user.subscribed:
            # Unsubscribe
            user_update = UserUpdate(subscribed=False)
            user_repository.update_user(phone, user_update)
            await whatsapp_service.send_subscription_changed_message(phone, False)
        else:
            # Subscribe  
            user_update = UserUpdate(subscribed=True)
            user_repository.update_user(phone, user_update)
            await whatsapp_service.send_subscription_changed_message(phone, True)
            
    except Exception as e:
        logger.error("Failed to handle subscription toggle",
                    phone=phone,
                    error=str(e),
                    error_type=type(e).__name__)


@router.get("/webhook/whatsapp")
async def whatsapp_webhook_verification():
    """
    Handle Twilio WhatsApp webhook verification.
    
    This endpoint handles GET requests to verify the webhook URL.
    Twilio doesn't use challenge-response like Facebook, it just sends GET requests.
    """
    try:
        # Log verification request
        logger.info("Twilio WhatsApp webhook verification request")
        
        # For Twilio, we can simply respond with 200 OK
        # Optionally validate using configured verify token
        return JSONResponse({"status": "webhook_verified", "service": "twilio"})
        
    except Exception as e:
        logger.error("Twilio WhatsApp webhook verification failed", error=str(e))
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/webhook/whatsapp/status")
async def whatsapp_status_callback(
    MessageSid: str = Form(...),
    MessageStatus: str = Form(...),
    To: str = Form(...),
    From: str = Form(...)
):
    """
    Handle Twilio WhatsApp message status callbacks.
    
    This endpoint receives delivery status updates for sent messages.
    Status values: queued, sent, delivered, read, failed, undelivered
    """
    try:
        # Remove 'whatsapp:' prefix from phone numbers
        to_phone = To[9:] if To.startswith("whatsapp:") else To
        from_phone = From[9:] if From.startswith("whatsapp:") else From
        
        logger.info("WhatsApp message status update",
                   message_sid=MessageSid,
                   status=MessageStatus,
                   to_phone=to_phone,
                   from_phone=from_phone)
        
        # Here you could update the message status in your database
        # For now, we'll just log the status update
        
        return PlainTextResponse("", status_code=200)
        
    except Exception as e:
        logger.error("Failed to process status callback", 
                    message_sid=MessageSid,
                    error=str(e))
        return PlainTextResponse("", status_code=500)