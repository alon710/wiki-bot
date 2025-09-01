from typing import List, Optional, Dict
import asyncio
from twilio.rest import Client
from twilio.base.exceptions import TwilioException

from src.config.settings import settings, Language
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
            if user and not user.is_in_session_window() and not settings.twilio.is_sandbox:
                should_use_template = True
                logger.info("User outside session window, should use template message",
                           phone=phone,
                           last_message_at=user.last_message_at)
            
            # Send message via Twilio
            # Note: Twilio client is synchronous, but we're wrapping it in async context
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
            # Format the message based on user's language
            if user.language == Language.HEBREW:
                formatted_message = f"🧠 עובדה יומית מרתקת:\n\n{fact_content}\n\n📚 מקור: ויקיפדיה"
            else:
                formatted_message = f"🧠 Daily Fun Fact:\n\n{fact_content}\n\n📚 Source: Wikipedia"
            
            message_id = await self.send_message(
                phone=user.phone,
                content=formatted_message,
                message_type=MessageType.DAILY_FACT
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send daily fact",
                        phone=user.phone,
                        language=user.language,
                        error=str(e))
            return False
    
    async def send_welcome_message(self, phone: str, language: Language) -> bool:
        """
        Send welcome message to a new user.
        
        Args:
            phone: User's phone number
            language: User's preferred language
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
                content = (
                    "🎉 ברוך הבא לבוט עובדות ויקיפדיה!\n\n"
                    "כל יום נשלח לך עובדה מעניינת ומרתקת מויקיפדיה.\n\n"
                    "פקודות זמינות:\n"
                    "• /english - החלף לאנגלית\n"
                    "• /hebrew - החלף לעברית\n"
                    "• /stop - הפסק קבלת עובדות\n"
                    "• /start - התחל קבלת עובדות\n"
                    "• /help - עזרה\n\n"
                    "תהנה מהעובדות היומיות! 🚀"
                )
            else:
                content = (
                    "🎉 Welcome to Wikipedia Facts Bot!\n\n"
                    "Every day we'll send you an interesting and fascinating fact from Wikipedia.\n\n"
                    "Available commands:\n"
                    "• /english - Switch to English\n"
                    "• /hebrew - Switch to Hebrew\n"
                    "• /stop - Stop receiving facts\n"
                    "• /start - Start receiving facts\n"
                    "• /help - Show this help\n\n"
                    "Enjoy your daily facts! 🚀"
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
                        language=language,
                        error=str(e))
            return False
    
    async def send_language_changed_message(self, phone: str, new_language: Language) -> bool:
        """
        Send language changed confirmation message.
        
        Args:
            phone: User's phone number
            new_language: New language preference
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if new_language == Language.HEBREW:
                content = "✅ השפה שונתה בהצלחה לעברית! העובדות היומיות יישלחו מעתה בעברית."
            else:
                content = "✅ Language changed successfully to English! Daily facts will now be sent in English."
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.LANGUAGE_CHANGED
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send language changed message",
                        phone=phone,
                        language=new_language,
                        error=str(e))
            return False
    
    async def send_subscription_changed_message(self, phone: str, subscribed: bool, language: Language) -> bool:
        """
        Send subscription status changed confirmation message.
        
        Args:
            phone: User's phone number
            subscribed: New subscription status
            language: User's language preference
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
                if subscribed:
                    content = "✅ המנוי חודש בהצלחה! תתחיל לקבל עובדות יומיות שוב."
                else:
                    content = "❌ המנוי בוטל בהצלחה. לא תקבל יותר עובדות יומיות. שלח /start כדי להתחיל שוב."
            else:
                if subscribed:
                    content = "✅ Subscription resumed successfully! You'll start receiving daily facts again."
                else:
                    content = "❌ Unsubscribed successfully. You won't receive daily facts anymore. Send /start to resume."
            
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
                        language=language,
                        error=str(e))
            return False
    
    async def send_help_message(self, phone: str, language: Language) -> bool:
        """
        Send help message with available commands.
        
        Args:
            phone: User's phone number
            language: User's language preference
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
                content = (
                    "📖 עזרה - בוט עובדות ויקיפדיה\n\n"
                    "פקודות זמינות:\n"
                    "• /english - החלף לאנגלית\n"
                    "• /hebrew - החלף לעברית\n"
                    "• /stop - הפסק קבלת עובדות\n"
                    "• /start - התחל קבלת עובדות\n"
                    "• /help - הצג עזרה זו\n\n"
                    "הבוט שולח עובדה מעניינת אחת ביום בשעה 09:00 UTC.\n\n"
                    "יש בעיה? צור קשר עם התמיכה שלנו."
                )
            else:
                content = (
                    "📖 Help - Wikipedia Facts Bot\n\n"
                    "Available commands:\n"
                    "• /english - Switch to English\n"
                    "• /hebrew - Switch to Hebrew\n"
                    "• /stop - Stop receiving facts\n"
                    "• /start - Start receiving facts\n"
                    "• /help - Show this help\n\n"
                    "The bot sends one interesting fact daily at 09:00 UTC.\n\n"
                    "Having issues? Contact our support team."
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
                        language=language,
                        error=str(e))
            return False
    
    async def send_error_message(self, phone: str, language: Language) -> bool:
        """
        Send error message for unrecognized commands.
        
        Args:
            phone: User's phone number
            language: User's language preference
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
                content = (
                    "❓ לא זיהיתי את הפקודה הזו.\n\n"
                    "שלח /help כדי לראות את הפקודות הזמינות."
                )
            else:
                content = (
                    "❓ I didn't recognize that command.\n\n"
                    "Send /help to see available commands."
                )
            
            message_id = await self.send_message(
                phone=phone,
                content=content,
                message_type=MessageType.ERROR
            )
            
            return message_id is not None
            
        except Exception as e:
            logger.error("Failed to send error message",
                        phone=phone,
                        language=language,
                        error=str(e))
            return False
    
    async def broadcast_daily_facts(self, users_by_language: Dict[Language, List[User]], facts_by_language: Dict[Language, str]) -> Dict[Language, int]:
        """
        Broadcast daily facts to all subscribed users by language.
        
        Args:
            users_by_language: Dictionary mapping languages to lists of users
            facts_by_language: Dictionary mapping languages to fact content
        
        Returns:
            Dictionary mapping languages to number of successful sends
        """
        results = {}
        
        for language, users in users_by_language.items():
            if language not in facts_by_language:
                logger.warning("No fact available for language", language=language)
                results[language] = 0
                continue
            
            fact_content = facts_by_language[language]
            successful_sends = 0
            
            logger.info("Starting broadcast for language",
                       language=language,
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
            
            results[language] = successful_sends
            logger.info("Broadcast completed for language",
                       language=language,
                       successful_sends=successful_sends,
                       total_users=len(users))
        
        return results
    
    async def send_sandbox_instructions(self, phone: str, language: Language) -> bool:
        """
        Send Twilio Sandbox join instructions to new users.
        
        Args:
            phone: User's phone number
            language: User's language preference
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
                content = (
                    "🔧 הודעה חשובה!\n\n"
                    "אתה משתמש בסביבת הבדיקות של Twilio WhatsApp.\n"
                    "כדי לקבל הודעות, עליך לשלוח תחילה את המסר:\n"
                    "join depend-wheat\n\n"
                    "שלח הודעה זו ל: whatsapp:+14155238886\n\n"
                    "לאחר מכן תוכל לחזור לכאן ולהתחיל להשתמש בבוט."
                )
            else:
                content = (
                    "🔧 Important Notice!\n\n"
                    "You are using the Twilio WhatsApp Sandbox.\n"
                    "To receive messages, you must first send:\n"
                    "join depend-wheat\n\n"
                    "Send this message to: whatsapp:+14155238886\n\n"
                    "After that, you can return here and start using the bot."
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
                        language=language,
                        error=str(e))
            return False
    
    async def send_main_menu(self, phone: str, language: Language, user=None) -> bool:
        """
        Send main menu with text options.
        
        Args:
            phone: User's phone number
            language: User's language preference
            user: User object for session tracking (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
                content = (
                    "🤖 בוט עובדות ויקיפדיה\n\n"
                    "בחר פעולה על ידי שליחת המספר המתאים:\n\n"
                    "1️⃣ קבל עובדה יומית\n"
                    "2️⃣ ניהול מנוי\n"
                    "3️⃣ שנה שפה\n"
                    "4️⃣ עזרה"
                )
            else:
                content = (
                    "🤖 Wikipedia Facts Bot\n\n"
                    "Choose an action by sending the corresponding number:\n\n"
                    "1️⃣ Get Daily Fact\n"
                    "2️⃣ Manage Subscription\n"
                    "3️⃣ Change Language\n"
                    "4️⃣ Help"
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
                        language=language,
                        error=str(e))
            return False
    
    async def send_subscription_menu(self, phone: str, language: Language, current_status: bool, user=None) -> bool:
        """
        Send subscription management menu.
        
        Args:
            phone: User's phone number
            language: User's language preference
            current_status: Current subscription status
            user: User object for session tracking (optional)
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if language == Language.HEBREW:
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
            else:
                if current_status:
                    content = (
                        "📬 Subscription Management\n\n"
                        "You are currently subscribed to daily facts.\n"
                        "Choose an action by sending the corresponding number:\n\n"
                        "1️⃣ Unsubscribe\n"
                        "0️⃣ Back to Main Menu"
                    )
                else:
                    content = (
                        "📬 Subscription Management\n\n"
                        "You are currently not subscribed to daily facts.\n"
                        "Choose an action by sending the corresponding number:\n\n"
                        "1️⃣ Subscribe\n"
                        "0️⃣ Back to Main Menu"
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