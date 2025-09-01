from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, BackgroundTasks, Form
from fastapi.responses import JSONResponse, PlainTextResponse

from src.config.settings import Language
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
    Body: str = Form(...),
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
        message_body = Body.strip()
        
        if not from_phone or not message_body:
            logger.warning("Missing required message fields", 
                         from_phone=from_phone, 
                         message_body=message_body)
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
            user_data = UserCreate(phone=phone, language=Language.ENGLISH)
            user = user_repository.create_user(user_data)
            
            # Send welcome message
            await whatsapp_service.send_welcome_message(phone, user.language)
            
            logger.info("New user created and welcomed", phone=phone)
            return
        
        # Process commands
        if body.startswith('/'):
            await handle_command(user, body)
        else:
            # Non-command message - send help
            await whatsapp_service.send_help_message(phone, user.language)
        
    except Exception as e:
        logger.error("Failed to process WhatsApp message",
                    phone=message.from_,
                    body=message.body,
                    error=str(e))


async def handle_command(user, command: str):
    """
    Handle WhatsApp commands.
    
    Args:
        user: User object
        command: Command string (e.g., '/start', '/stop')
    """
    try:
        phone = user.phone
        current_language = user.language
        
        if command in ['/start', '/subscribe']:
            # Start receiving daily facts
            if not user.subscribed:
                user_update = UserUpdate(subscribed=True)
                user_repository.update_user(phone, user_update)
            
            await whatsapp_service.send_subscription_changed_message(
                phone, True, current_language
            )
            
        elif command in ['/stop', '/unsubscribe']:
            # Stop receiving daily facts
            if user.subscribed:
                user_update = UserUpdate(subscribed=False)
                user_repository.update_user(phone, user_update)
            
            await whatsapp_service.send_subscription_changed_message(
                phone, False, current_language
            )
            
        elif command in ['/english', '/en']:
            # Change language to English
            if current_language != Language.ENGLISH:
                user_update = UserUpdate(language=Language.ENGLISH)
                user_repository.update_user(phone, user_update)
                
                await whatsapp_service.send_language_changed_message(
                    phone, Language.ENGLISH
                )
            else:
                await whatsapp_service.send_language_changed_message(
                    phone, Language.ENGLISH
                )
        
        elif command in ['/hebrew', '/he', '/עברית']:
            # Change language to Hebrew
            if current_language != Language.HEBREW:
                user_update = UserUpdate(language=Language.HEBREW)
                user_repository.update_user(phone, user_update)
                
                await whatsapp_service.send_language_changed_message(
                    phone, Language.HEBREW
                )
            else:
                await whatsapp_service.send_language_changed_message(
                    phone, Language.HEBREW
                )
        
        elif command in ['/help', '/h']:
            # Send help message
            await whatsapp_service.send_help_message(phone, current_language)
        
        else:
            # Unknown command
            await whatsapp_service.send_error_message(phone, current_language)
        
        logger.info("Command processed successfully",
                   phone=phone,
                   command=command)
        
    except Exception as e:
        logger.error("Failed to handle command",
                    phone=user.phone,
                    command=command,
                    error=str(e))


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