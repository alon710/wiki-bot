from typing import List, Optional, Dict
import asyncio
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from src.config.settings import settings
from src.models.message import WhatsAppMessage, MessageType
from src.models.user import User
from src.utils.logger import get_logger

logger = get_logger(__name__)


class WhatsAppService:
    """Service for sending WhatsApp messages via Twilio."""
    
    def __init__(self):
        """Initialize Twilio client."""
        self.client = Client(settings.twilio.account_sid, settings.twilio.auth_token)
        
        # Log sandbox detection
        if settings.twilio.is_sandbox:
            logger.warning("Using Twilio WhatsApp Sandbox - users must join sandbox first")
        else:
            logger.info("Using Twilio WhatsApp Business API")
        
        if not settings.twilio.has_templates:
            logger.warning("No WhatsApp templates configured - messages may fail outside session window")
        
        logger.info("WhatsApp service initialized")
    
    def _get_template_sid(self, message_type: MessageType) -> Optional[str]:
        """Get template SID for message type."""
        template_mapping = {
            MessageType.WELCOME: settings.twilio.welcome_template_sid,
            MessageType.SUBSCRIPTION_CHANGED: settings.twilio.subscription_template_sid,
            MessageType.LANGUAGE_CHANGED: settings.twilio.language_template_sid,
        }
        return template_mapping.get(message_type) or settings.twilio.menu_template_sid
    
    def _format_template_variables(self, message_type: MessageType, content: str, user=None) -> str:
        """Format template variables for WhatsApp templates."""
        # For now, just use content as variable 1
        # In production, you'd extract specific variables based on template structure
        import json
        return json.dumps({"1": content})
    
    async def send_message(self, phone: str, content: str, message_type: MessageType, user=None) -> Optional[str]:
        """
        Send a WhatsApp message to a specific phone number.
        
        Args:
            phone: Recipient phone number (without whatsapp: prefix)
            content: Message content
            message_type: Type of message being sent
            user: User object to check session status (optional)
        
        Returns:
            Message ID (SID) if successful, None if failed
        """
        try:
            WhatsAppMessage(
                to=phone,
                content=content,
                message_type=message_type
            )
            
            # Format phone number with whatsapp: prefix if not already present
            to_number = phone if phone.startswith('whatsapp:') else f'whatsapp:{phone}'
            
            # Check if we need to use template message
            should_use_template = False
            template_sid = None
            template_variables = None
            
            if user and not user.is_in_session_window() and not settings.twilio.is_sandbox and settings.twilio.has_templates:
                should_use_template = True
                template_sid = self._get_template_sid(message_type)
                template_variables = self._format_template_variables(message_type, content, user)
                logger.info("User outside session window, using template message",
                           phone=phone,
                           template_sid=template_sid,
                           last_message_at=user.last_message_at)
            
            # Send message via Twilio
            # Note: Twilio client is synchronous, but we're wrapping it in async context
            if should_use_template and template_sid:
                # Use template message
                response = self.client.messages.create(
                    content_sid=template_sid,
                    content_variables=template_variables,
                    from_=settings.twilio.whatsapp_from,
                    to=to_number
                )
            else:
                # Use regular message (sandbox or session window)
                response = self.client.messages.create(
                    body=content,
                    from_=settings.twilio.whatsapp_from,
                    to=to_number
                )
            
            # Twilio returns message SID
            external_id = response.sid if response else None
            
            logger.info("WhatsApp message sent successfully",
                       phone=phone,
                       message_type=message_type,
                       external_id=external_id,
                       sandbox=settings.twilio.is_sandbox,
                       should_use_template=should_use_template)
            
            return external_id
            
        except TwilioException as e:
            logger.error("Twilio API error when sending WhatsApp message",
                        phone=phone,
                        message_type=message_type,
                        error_code=getattr(e, 'code', None),
                        error_message=str(e),
                        sandbox=settings.twilio.is_sandbox)
            return None
        except Exception as e:
            logger.error("Failed to send WhatsApp message",
                        phone=phone,
                        message_type=message_type,
                        error=str(e),
                        sandbox=settings.twilio.is_sandbox)
            return None
    
    async def send_daily_fact(self, user: User, fact_content: str) -> bool:
        """
        Send daily fact to a user.
        
        Args:
            user: User to send the fact to
            fact_content: The daily fact content
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format the message in Hebrew
            formatted_message = f"🧠 עובדה יומית מרתקת:\n\n{fact_content}\n\n📚 מקור: ויקיפדיה"
            
            message_id = await self.send_message(
                phone=user.phone,
                content=formatted_message,
                message_type=MessageType.DAILY_FACT
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send daily fact",
                        phone=user.phone,
                        error=str(e))
            return False
    
    async def send_welcome_message(self, phone: str, user: User = None) -> bool:
        """
        Send welcome message when user first interacts.
        
        Args:
            phone: User's phone number
            user: User object (for session-based messages)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if settings.twilio.is_sandbox:
                content = (
                    "🎉 ברוך הבא לבוט העובדות הישראלי!"
                    "\n\nכדי לקבל הודעות, תצטרך להצטרף ל-WhatsApp Sandbox של Twilio. "
                    "שלח את הודעת הקוד הבא ל- +1 (415) 523-8886:"
                    "\n\njoin @sandbox_keyword"
                    "\n\nלאחר ההצטרפות, תקבל עובדה מעניינת כל יום בשעה 09:00 UTC.\n\n"
                    "בחר אפשרות מהתפריט:"
                    "\n1️⃣ עובדה יומית"
                    "\n2️⃣ הפסק מנוי"
                    "\n3️⃣ עזרה"
                )
            else:
                content = (
                    "🎉 ברוך הבא לבוט העובדות הישראלי!"
                    "\n\nתקבל עובדה מעניינת כל יום בשעה 09:00 UTC.\n\n"
                    "בחר אפשרות מהתפריט:"
                    "\n1️⃣ עובדה יומית"
                    "\n2️⃣ הפסק מנוי"
                    "\n3️⃣ עזרה"
                )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.WELCOME
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send welcome message",
                        phone=phone,
                        error=str(e))
            return False
    
    
    async def send_subscription_changed_message(self, phone: str, subscribed: bool) -> bool:
        """
        Send subscription status changed confirmation message.
        
        Args:
            phone: User's phone number
            subscribed: New subscription status
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if subscribed:
                content = "✅ המנוי חודש בהצלחה! תתחיל לקבל עובדות יומיות שוב."
            else:
                content = "❌ המנוי בוטל בהצלחה. לא תקבל יותר עובדות יומיות. שלח /start כדי להתחיל שוב."
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.SUBSCRIPTION_CHANGED
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send subscription changed message",
                        phone=phone,
                        subscribed=subscribed,
                        error=str(e))
            return False
    
    async def send_help_message(self, phone: str) -> bool:
        """
        Send help message with available options.
        
        Args:
            phone: User's phone number
        
        Returns:
            True if successful, False otherwise
        """
        try:
            content = (
                "📖 עזרה - בוט עובדות ויקיפדיה\n\n"
                "אפשרויות זמינות:\n"
                "1️⃣ עובדה יומית\n"
                "2️⃣ הפסק מנוי\n"
                "3️⃣ עזרה\n\n"
                "הבוט שולח עובדה מעניינת אחת ביום בשעה 09:00 UTC.\n\n"
                "יש בעיה? צור קשר עם התמיכה שלנו."
            )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.HELP
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send help message",
                        phone=phone,
                        error=str(e))
            return False
    
    async def send_main_menu(self, phone: str, user: User = None) -> bool:
        """
        Send main menu for invalid input.
        
        Args:
            phone: User's phone number
            user: User object (for session-based messages)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            content = (
                "❓ אנא בחר מספר מהתפריט:\n\n"
                "1️⃣ עובדה יומית\n"
                "2️⃣ הפסק מנוי\n"
                "3️⃣ עזרה"
            )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.ERROR
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send main menu",
                        phone=phone,
                        error=str(e))
            return False
    
    async def broadcast_daily_facts_hebrew(self, users: List[User], fact_content: str) -> int:
        """
        Broadcast daily facts to all subscribed users in Hebrew.
        
        Args:
            users: List of users to send facts to
            fact_content: The daily fact content in Hebrew
        
        Returns:
            Number of successful sends
        """
        successful_sends = 0
        
        logger.info("Starting Hebrew daily fact broadcast",
                   user_count=len(users))
        
        # Send to users in batches to avoid overwhelming the API
        batch_size = 10
        for i in range(0, len(users), batch_size):
            batch = users[i:i + batch_size]
            batch_tasks = []
            
            for user in batch:
                task = self.send_daily_fact(user, fact_content)
                batch_tasks.append(task)
            
            # Execute batch
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)
            
            # Count successful sends
            for result in batch_results:
                if isinstance(result, bool) and result:
                    successful_sends += 1
                elif isinstance(result, Exception):
                    logger.error("Batch send error", error=str(result))
            
            # Small delay between batches to be respectful to the API
            if i + batch_size < len(users):
                await asyncio.sleep(1)
        
        logger.info("Hebrew daily fact broadcast completed",
                   successful_sends=successful_sends,
                   total_users=len(users))
        
        return successful_sends
    
    async def send_sandbox_instructions(self, phone: str) -> bool:
        """
        Send Twilio Sandbox join instructions to new users.
        
        Args:
            phone: User's phone number
        
        Returns:
            True if successful, False otherwise
        """
        try:
            content = (
                "🔧 הודעה חשובה!\n\n"
                "אתה משתמש בסביבת הבדיקות של Twilio WhatsApp.\n"
                "כדי לקבל הודעות, עליך לשלוח תחילה את המסר:\n"
                "join depend-wheat\n\n"
                "שלח הודעה זו ל: whatsapp:+14155238886\n\n"
                "לאחר מכן תוכל לחזור לכאן ולהתחיל להשתמש בבוט."
            )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.WELCOME
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send sandbox instructions",
                        phone=phone,
                        error=str(e))
            return False
    
    async def send_main_menu(self, phone: str, user=None) -> bool:
        """
        Send main menu with text options (Hebrew only).
        
        Args:
            phone: User's phone number
            user: User object for session tracking (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            content = (
                "🤖 בוט עובדות ויקיפדיה\n\n"
                "בחר פעולה על ידי שליחת המספר המתאים:\n\n"
                "1️⃣ קבל עובדה יומית\n"
                "2️⃣ ניהול מנוי\n"
                "3️⃣ עזרה"
            )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.WELCOME,
                user=user
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send main menu",
                        phone=phone,
                        error=str(e))
            return False
    
    async def send_subscription_menu(self, phone: str, current_status: bool, user=None) -> bool:
        """
        Send subscription management menu (Hebrew only).
        
        Args:
            phone: User's phone number
            current_status: Current subscription status
            user: User object for session tracking (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if current_status:
                content = (
                    "📬 ניהול מנוי\n\n"
                    "אתה כרגע מנוי לעובדות יומיות.\n"
                    "בחר פעולה על ידי שליחת המספר המתאים:\n\n"
                    "1️⃣ בטל מנוי\n"
                    "0️⃣ חזור לתפריט הראשי"
                )
            else:
                content = (
                    "📬 ניהול מנוי\n\n"
                    "אתה כרגע לא מנוי לעובדות יומיות.\n"
                    "בחר פעולה על ידי שליחת המספר המתאים:\n\n"
                    "1️⃣ הרשם למנוי\n"
                    "0️⃣ חזור לתפריט הראשי"
                )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.SUBSCRIPTION_CHANGED
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send subscription menu",
                        phone=phone,
                        language=language,
                        error=str(e))
            return False
    
    async def send_language_menu(self, phone: str, current_language: Language) -> bool:
        """
        Send language selection menu.
        
        Args:
            phone: User's phone number
            current_language: Current language preference
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if current_language == Language.HEBREW:
                content = (
                    "🌍 בחירת שפה\n\n"
                    "בחר את השפה המועדפת עליך על ידי שליחת המספר המתאים:\n\n"
                    "1️⃣ English\n"
                    "2️⃣ עברית\n"
                    "0️⃣ חזור לתפריט הראשי"
                )
            else:
                content = (
                    "🌍 Language Selection\n\n"
                    "Choose your preferred language by sending the corresponding number:\n\n"
                    "1️⃣ English\n"
                    "2️⃣ עברית (Hebrew)\n"
                    "0️⃣ Back to Main Menu"
                )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.LANGUAGE_CHANGED
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send language menu",
                        phone=phone,
                        current_language=current_language,
                        error=str(e))
            return False


# Global service instance
whatsapp_service = WhatsAppService()