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
        return {"type": "HEADER", "format": "TEXT", "text": text}

    @staticmethod
    def body(text: str, variables: List[str] | None = None) -> Dict:
        """Create a body component with optional variables."""
        component = {"type": "BODY", "text": text}

        if variables:
            component["example"] = {"body_text": [variables]}

        return component

    @staticmethod
    def footer(text: str) -> Dict:
        """Create a footer component."""
        return {"type": "FOOTER", "text": text}

    @staticmethod
    def button_url(text: str, url: str) -> Dict:
        """Create a URL button component."""
        return {
            "type": "BUTTONS",
            "buttons": [{"type": "URL", "text": text, "url": url}],
        }

    @staticmethod
    def button_quick_reply(buttons: List[str]) -> Dict:
        """Create quick reply buttons."""
        return {
            "type": "BUTTONS",
            "buttons": [{"type": "QUICK_REPLY", "text": button} for button in buttons],
        }


