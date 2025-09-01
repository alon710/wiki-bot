from typing import List, Optional
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

        if settings.twilio.is_sandbox:
            logger.warning(
                "Using Twilio WhatsApp Sandbox - users must join sandbox first"
            )
        else:
            logger.info("Using Twilio WhatsApp Business API")

        if not settings.twilio.has_templates:
            logger.warning(
                "No WhatsApp templates configured - messages may fail outside session window"
            )

        logger.info("WhatsApp service initialized")

    def get_available_templates(self) -> dict:
        """Get all available template SIDs."""
        return {
            "welcome": settings.twilio.welcome_template_sid,
            "menu": settings.twilio.menu_template_sid,
            "subscription": settings.twilio.subscription_template_sid,
            "language": settings.twilio.language_template_sid,
            "daily_fact": settings.twilio.daily_fact_template_sid,
            "help": settings.twilio.help_template_sid,
        }

    def is_template_available(self, message_type: MessageType) -> bool:
        """Check if template is available for message type."""
        template_sid = self._get_template_sid(message_type)
        return bool(template_sid)

    def _get_template_sid(self, message_type: MessageType) -> Optional[str]:
        """Get template SID for message type."""
        template_mapping = {
            MessageType.WELCOME: settings.twilio.welcome_template_sid,
            MessageType.SUBSCRIPTION_CHANGED: settings.twilio.subscription_template_sid,
            MessageType.LANGUAGE_CHANGED: settings.twilio.language_template_sid,
            MessageType.DAILY_FACT: settings.twilio.daily_fact_template_sid,
            MessageType.HELP: settings.twilio.help_template_sid,
        }
        return template_mapping.get(message_type) or settings.twilio.menu_template_sid

    def _format_template_variables(
        self, message_type: MessageType, content: str, user: Optional[User] = None
    ) -> str:
        """Format template variables for WhatsApp templates."""

        import json

        # Basic template variables - customize per message type
        variables = {"1": content}
        
        # Message type specific variables
        if message_type == MessageType.DAILY_FACT:
            variables["2"] = "ויקיפדיה"  # Source
            if user:
                variables["3"] = user.phone  # Can be used for personalization
        elif message_type == MessageType.WELCOME:
            variables["2"] = "09:00 UTC"  # Delivery time
        elif user:
            variables["2"] = user.phone  # Can be used for personalization
        
        return json.dumps(variables)

    async def send_message(
        self, phone: str, content: str, message_type: MessageType, user: Optional[User] = None
    ) -> Optional[str]:
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
            WhatsAppMessage(to=phone, content=content, message_type=message_type)

            to_number = phone if phone.startswith("whatsapp:") else f"whatsapp:{phone}"

            should_use_template = False
            template_sid = None
            template_variables = None

            if (
                user
                and not user.is_in_session_window()
                and not settings.twilio.is_sandbox
                and settings.twilio.has_templates
            ):
                template_sid = self._get_template_sid(message_type)
                if template_sid:
                    should_use_template = True
                    template_variables = self._format_template_variables(
                        message_type, content, user
                    )
                    logger.info(
                        "User outside session window, using template message",
                        phone=phone,
                        template_sid=template_sid,
                        last_message_at=user.last_message_at,
                    )
                else:
                    logger.warning(
                        "Template required but not available, falling back to regular message",
                        phone=phone,
                        message_type=message_type,
                    )

            if should_use_template and template_sid:
                response = self.client.messages.create(
                    content_sid=template_sid,
                    content_variables=template_variables,
                    from_=settings.twilio.whatsapp_from,
                    to=to_number,
                )
            else:
                response = self.client.messages.create(
                    body=content, from_=settings.twilio.whatsapp_from, to=to_number
                )

            external_id = response.sid if response else None

            # Verify the response and log details
            if external_id:
                logger.info(
                    "WhatsApp message sent successfully",
                    phone=phone,
                    message_type=message_type,
                    external_id=external_id,
                    sandbox=settings.twilio.is_sandbox,
                    should_use_template=should_use_template,
                    response_status=getattr(response, 'status', 'unknown'),
                )
            else:
                logger.warning(
                    "WhatsApp message sent but no SID received",
                    phone=phone,
                    message_type=message_type,
                    sandbox=settings.twilio.is_sandbox,
                    should_use_template=should_use_template,
                )

            return external_id

        except TwilioException as e:
            logger.error(
                "Twilio API error when sending WhatsApp message",
                phone=phone,
                message_type=message_type,
                error_code=getattr(e, "code", None),
                error_message=str(e),
                sandbox=settings.twilio.is_sandbox,
                should_use_template=should_use_template,
                template_sid=template_sid,
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to send WhatsApp message",
                phone=phone,
                message_type=message_type,
                error=str(e),
                error_type=type(e).__name__,
                sandbox=settings.twilio.is_sandbox,
                should_use_template=should_use_template,
            )
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
            formatted_message = (
                f"🧠 עובדה יומית מרתקת:\n\n{fact_content}\n\n📚 מקור: ויקיפדיה"
            )

            message_id = await self.send_message(
                phone=user.phone,
                content=formatted_message,
                message_type=MessageType.DAILY_FACT,
                user=user,
            )

            return message_id is not None

        except Exception as e:
            logger.error("Failed to send daily fact", phone=user.phone, error=str(e))
            return False

    async def send_welcome_message(self, phone: str, user: Optional[User] = None) -> bool:
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
                phone=phone, content=content, message_type=MessageType.WELCOME
            )

            return message_id is not None

        except Exception as e:
            logger.error("Failed to send welcome message", phone=phone, error=str(e))
            return False

    async def send_subscription_changed_message(
        self, phone: str, subscribed: bool
    ) -> bool:
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
                message_type=MessageType.SUBSCRIPTION_CHANGED,
            )

            return message_id is not None

        except Exception as e:
            logger.error(
                "Failed to send subscription changed message",
                phone=phone,
                subscribed=subscribed,
                error=str(e),
            )
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
                phone=phone, content=content, message_type=MessageType.HELP
            )

            return message_id is not None

        except Exception as e:
            logger.error("Failed to send help message", phone=phone, error=str(e))
            return False

    async def send_main_menu(self, phone: str, user: Optional[User] = None) -> bool:
        """
        Send main menu for invalid input.

        Args:
            phone: User's phone number
            user: User object (for session-based messages)

        Returns:
            True if successful, False otherwise
        """
        try:
            content = "❓ אנא בחר מספר מהתפריט:\n\n1️⃣ עובדה יומית\n2️⃣ הפסק מנוי\n3️⃣ עזרה"

            message_id = await self.send_message(
                phone=phone, content=content, message_type=MessageType.ERROR, user=user
            )

            return message_id is not None

        except Exception as e:
            logger.error("Failed to send main menu", phone=phone, error=str(e))
            return False

    async def broadcast_daily_facts_hebrew(
        self, users: List[User], fact_content: str
    ) -> int:
        """
        Broadcast daily facts to all subscribed users in Hebrew.

        Args:
            users: List of users to send facts to
            fact_content: The daily fact content in Hebrew

        Returns:
            Number of successful sends
        """
        successful_sends = 0

        logger.info("Starting Hebrew daily fact broadcast", user_count=len(users))

        batch_size = 10
        for i in range(0, len(users), batch_size):
            batch = users[i : i + batch_size]
            batch_tasks = []

            for user in batch:
                task = self.send_daily_fact(user, fact_content)
                batch_tasks.append(task)

            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for result in batch_results:
                if isinstance(result, bool) and result:
                    successful_sends += 1
                elif isinstance(result, Exception):
                    logger.error("Batch send error", error=str(result))

            if i + batch_size < len(users):
                await asyncio.sleep(1)

        logger.info(
            "Hebrew daily fact broadcast completed",
            successful_sends=successful_sends,
            total_users=len(users),
        )

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
                phone=phone, content=content, message_type=MessageType.WELCOME
            )

            return message_id is not None

        except Exception as e:
            logger.error(
                "Failed to send sandbox instructions", phone=phone, error=str(e)
            )
            return False



whatsapp_service = WhatsAppService()
