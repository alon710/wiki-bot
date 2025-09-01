#!/usr/bin/env python3
"""
WhatsApp Template Management Script

This script helps you create and manage WhatsApp templates for your Twilio account.
Run with: python scripts/manage_templates.py
"""

import sys
from pathlib import Path


from twilio.rest import Client
from src.config.settings import settings
from src.utils.template_helper import get_template_examples
from src.utils.logger import get_logger

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

logger = get_logger(__name__)


class TemplateManager:
    """Manage WhatsApp templates via Twilio API."""

    def __init__(self):
        """Initialize Twilio client."""
        self.client = Client(settings.twilio.account_sid, settings.twilio.auth_token)
        self.account_sid = settings.twilio.account_sid

    def list_templates(self):
        """List all existing templates."""
        try:
            templates = self.client.content.v1.contents.list()

            print("\n📋 Existing WhatsApp Templates:")
            print("-" * 50)

            for template in templates:
                print(f"Name: {template.friendly_name}")
                print(f"SID: {template.sid}")
                print(f"Language: {template.language}")
                print(f"Status: {template.approval_requests}")
                print("-" * 30)

            return templates

        except Exception as e:
            logger.error("Failed to list templates", error=str(e))
            return []

    def create_template(self, template_name: str, template_data: dict):
        """Create a new WhatsApp template."""
        try:
            print(f"\n🔨 Creating template: {template_name}")

            content = self.client.content.v1.contents.create(
                friendly_name=template_name,
                language=template_data["language"],
                variables={},
                types={"twilio/text": {"body": template_data["components"][0]["text"]}},
            )

            print("✅ Template created successfully!")
            print(f"   SID: {content.sid}")
            print(f"   Name: {content.friendly_name}")

            return content.sid

        except Exception as e:
            logger.error(
                "Failed to create template", template_name=template_name, error=str(e)
            )
            print(f"❌ Failed to create template {template_name}: {str(e)}")
            return None

    def create_all_templates(self):
        """Create all predefined Hebrew templates."""
        templates = get_template_examples()
        created_templates = {}

        print("\n🚀 Creating all Hebrew templates...")

        for name, template_data in templates.items():
            sid = self.create_template(name, template_data)
            if sid:
                created_templates[name] = sid

        if created_templates:
            print("\n📝 Add these SIDs to your .env file:")
            print("-" * 50)

            mapping = {
                "welcome_hebrew": "TWILIO_WELCOME_TEMPLATE_SID",
                "daily_fact_hebrew": "TWILIO_DAILY_FACT_TEMPLATE_SID",
                "help_hebrew": "TWILIO_HELP_TEMPLATE_SID",
                "subscription_changed_hebrew": "TWILIO_SUBSCRIPTION_TEMPLATE_SID",
                "menu_hebrew": "TWILIO_MENU_TEMPLATE_SID",
            }

            for template_name, sid in created_templates.items():
                env_var = mapping.get(
                    template_name, f"TWILIO_{template_name.upper()}_SID"
                )
                print(f"{env_var}={sid}")

        return created_templates

    def show_template_examples(self):
        """Show example template structures."""
        templates = get_template_examples()

        print("\n📖 Template Examples:")
        print("=" * 60)

        for name, template_data in templates.items():
            print(f"\n🏷️  Template: {name}")
            print(f"   Language: {template_data['language']}")
            print(f"   Category: {template_data['category']}")
            print(f"   Body: {template_data['components'][0]['text']}")

            if "example" in template_data["components"][0]:
                print(
                    f"   Variables: {template_data['components'][0]['example']['body_text']}"
                )

            print("-" * 40)


def main():
    """Main CLI interface."""
    manager = TemplateManager()

    print("🤖 WhatsApp Template Manager")
    print("=" * 40)

    while True:
        print("\nSelect an option:")
        print("1. List existing templates")
        print("2. Create all Hebrew templates")
        print("3. Show template examples")
        print("4. Exit")

        choice = input("\nEnter your choice (1-4): ").strip()

        if choice == "1":
            manager.list_templates()

        elif choice == "2":
            confirm = input("⚠️  This will create new templates. Continue? (y/N): ")
            if confirm.lower() == "y":
                manager.create_all_templates()

        elif choice == "3":
            manager.show_template_examples()

        elif choice == "4":
            print("👋 Goodbye!")
            break

        else:
            print("❌ Invalid choice. Please select 1-4.")


if __name__ == "__main__":
    main()
