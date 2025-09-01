"""
WhatsApp Template Helper Utilities

This module provides utilities for creating and managing WhatsApp message templates.
"""

from typing import Dict, List
from enum import Enum


class TemplateLanguage(str, Enum):
    """Supported template languages."""
    
    HEBREW = "he"
    ENGLISH = "en"


class TemplateCategory(str, Enum):
    """WhatsApp template categories."""
    
    UTILITY = "UTILITY"
    MARKETING = "MARKETING"
    AUTHENTICATION = "AUTHENTICATION"


class TemplateComponent:
    """Helper class for building template components."""
    
    @staticmethod
    def header(text: str) -> Dict:
        """Create a header component."""
        return {
            "type": "HEADER",
            "format": "TEXT",
            "text": text
        }
    
    @staticmethod
    def body(text: str, variables: List[str] = None) -> Dict:
        """Create a body component with optional variables."""
        component = {
            "type": "BODY",
            "text": text
        }
        
        if variables:
            component["example"] = {
                "body_text": [variables]
            }
        
        return component
    
    @staticmethod
    def footer(text: str) -> Dict:
        """Create a footer component."""
        return {
            "type": "FOOTER",
            "text": text
        }
    
    @staticmethod
    def button_url(text: str, url: str) -> Dict:
        """Create a URL button component."""
        return {
            "type": "BUTTONS",
            "buttons": [{
                "type": "URL",
                "text": text,
                "url": url
            }]
        }
    
    @staticmethod
    def button_quick_reply(buttons: List[str]) -> Dict:
        """Create quick reply buttons."""
        return {
            "type": "BUTTONS",
            "buttons": [
                {
                    "type": "QUICK_REPLY",
                    "text": button
                } for button in buttons
            ]
        }


def create_template_request(
    name: str,
    language: TemplateLanguage,
    category: TemplateCategory,
    components: List[Dict]
) -> Dict:
    """
    Create a WhatsApp template creation request.
    
    Args:
        name: Template name (lowercase, underscores only)
        language: Template language
        category: Template category
        components: List of template components
    
    Returns:
        Dictionary ready for Twilio API
    """
    return {
        "name": name,
        "language": language.value,
        "category": category.value,
        "components": components
    }


# Predefined Hebrew templates for the bot
HEBREW_TEMPLATES = {
    "welcome_hebrew": create_template_request(
        name="welcome_hebrew",
        language=TemplateLanguage.HEBREW,
        category=TemplateCategory.UTILITY,
        components=[
            TemplateComponent.body(
                "🎉 ברוך הבא לבוט העובדות הישראלי!\n\n"
                "תקבל עובדה מעניינת כל יום בשעה {{1}}.\n\n"
                "בחר אפשרות מהתפריט:\n"
                "1️⃣ עובדה יומית\n"
                "2️⃣ הפסק מנוי\n"
                "3️⃣ עזרה",
                variables=["09:00 UTC"]
            )
        ]
    ),
    
    "daily_fact_hebrew": create_template_request(
        name="daily_fact_hebrew",
        language=TemplateLanguage.HEBREW,
        category=TemplateCategory.UTILITY,
        components=[
            TemplateComponent.body(
                "🧠 עובדה יומית מרתקת:\n\n"
                "{{1}}\n\n"
                "📚 מקור: {{2}}",
                variables=["תוכן העובדה כאן", "ויקיפדיה"]
            )
        ]
    ),
    
    "help_hebrew": create_template_request(
        name="help_hebrew",
        language=TemplateLanguage.HEBREW,
        category=TemplateCategory.UTILITY,
        components=[
            TemplateComponent.body(
                "📖 עזרה - בוט עובדות ויקיפדיה\n\n"
                "אפשרויות זמינות:\n"
                "1️⃣ עובדה יומית\n"
                "2️⃣ הפסק מנוי\n"
                "3️⃣ עזרה\n\n"
                "הבוט שולח עובדה מעניינת אחת ביום בשעה 09:00 UTC.\n\n"
                "יש בעיה? צור קשר עם התמיכה שלנו."
            )
        ]
    ),
    
    "subscription_changed_hebrew": create_template_request(
        name="subscription_changed_hebrew",
        language=TemplateLanguage.HEBREW,
        category=TemplateCategory.UTILITY,
        components=[
            TemplateComponent.body("{{1}}", variables=["הודעת שינוי מנוי"])
        ]
    ),
    
    "menu_hebrew": create_template_request(
        name="menu_hebrew",
        language=TemplateLanguage.HEBREW,
        category=TemplateCategory.UTILITY,
        components=[
            TemplateComponent.body(
                "❓ אנא בחר מספר מהתפריט:\n\n"
                "1️⃣ עובדה יומית\n"
                "2️⃣ הפסק מנוי\n"
                "3️⃣ עזרה"
            )
        ]
    )
}


def get_template_examples():
    """Get example template requests for all Hebrew templates."""
    return HEBREW_TEMPLATES