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
        logger.debug("User lookup completed", 
                    phone=phone, 
                    user_found=user is not None,
                    user_id=user.id if user else None)
        
        if not user:
            # New user - create with default settings
            user_data = UserCreate(phone=phone, language=Language.ENGLISH)
            user = user_repository.create_user(user_data)
            
            logger.debug("New user created", 
                        phone=phone, 
                        user_id=user.id,
                        user_language=user.language)
            
            # Send main menu for new users
            await whatsapp_service.send_main_menu(phone, user.language)
            
            logger.info("New user created and main menu sent", phone=phone)
            return
        
        # Process number responses or show main menu for any text message
        if body and body.strip().isdigit():
            await handle_number_response(phone, body.strip())
        else:
            # Any non-number message should get main menu
            await whatsapp_service.send_main_menu(phone, user.language)
        
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
        logger.debug("Processing number response", phone=phone, number=number)
        
        # Get fresh user data to avoid session issues
        user = user_repository.get_user_by_phone(phone)
        if not user:
            logger.warning("User not found for number processing", phone=phone)
            return
            
        current_language = user.language
        logger.debug("User data retrieved for number", 
                    phone=phone, 
                    language=current_language, 
                    subscribed=user.subscribed)
        
        # Main menu responses
        if number == "1":
            # Get Daily Fact - for now send help until we implement fact fetching
            await whatsapp_service.send_help_message(phone, current_language)
            
        elif number == "2":
            # Manage Subscription - show subscription menu
            await whatsapp_service.send_subscription_menu(phone, current_language, user.subscribed)
            
        elif number == "3":
            # Change Language - show language menu
            await whatsapp_service.send_language_menu(phone, current_language)
            
        elif number == "4":
            # Help
            await whatsapp_service.send_help_message(phone, current_language)
            
        elif number == "0":
            # Back to main menu
            await whatsapp_service.send_main_menu(phone, current_language)
            
        else:
            # Handle subscription and language menu responses
            await handle_sub_menu_response(phone, number, user)
        
        logger.info("Number response processed successfully",
                   phone=phone,
                   number=number)
        
    except Exception as e:
        logger.error("Failed to handle number response",
                    phone=phone,
                    number=number,
                    error=str(e),
                    error_type=type(e).__name__)


async def handle_sub_menu_response(phone: str, number: str, user):
    """Handle responses in subscription and language sub-menus."""
    try:
        current_language = user.language
        
        # This could be subscription menu (1=subscribe/unsubscribe, 0=back)
        # or language menu (1=English, 2=Hebrew, 0=back)
        
        if number == "1":
            # Check if we're in subscription context or language context
            # For now, assume it's subscription toggle
            if user.subscribed:
                # Unsubscribe
                user_update = UserUpdate(subscribed=False)
                user_repository.update_user(phone, user_update)
                logger.debug("User subscription updated", phone=phone, subscribed=False)
                await whatsapp_service.send_subscription_changed_message(
                    phone, False, current_language
                )
            else:
                # Subscribe  
                user_update = UserUpdate(subscribed=True)
                user_repository.update_user(phone, user_update)
                logger.debug("User subscription updated", phone=phone, subscribed=True)
                await whatsapp_service.send_subscription_changed_message(
                    phone, True, current_language
                )
                
        elif number == "2":
            # Language menu: Hebrew
            if current_language != Language.HEBREW:
                user_update = UserUpdate(language=Language.HEBREW)
                user_repository.update_user(phone, user_update)
                logger.debug("User language updated", phone=phone, language="Hebrew")
                await whatsapp_service.send_language_changed_message(
                    phone, Language.HEBREW
                )
            else:
                await whatsapp_service.send_language_changed_message(
                    phone, Language.HEBREW
                )
        else:
            # Unknown number - show main menu
            await whatsapp_service.send_main_menu(phone, current_language)
            
    except Exception as e:
        logger.error("Failed to handle sub menu response",
                    phone=phone,
                    number=number,
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