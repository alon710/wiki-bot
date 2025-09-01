from pathlib import Path
from enum import Enum

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl

ENV_FILE = Path(__file__).parent.parent.parent / ".env"


class Environment(str, Enum):
    LOCAL = "local"
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# Removed multi-language support - Hebrew only bot


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DATABASE_", env_file=ENV_FILE, extra="ignore"
    )

    url: str = Field(alias="DATABASE_URL")
    echo: bool = Field(alias="DATABASE_ECHO", default=False)
    pool_size: int = Field(alias="DATABASE_POOL_SIZE", default=5)
    max_overflow: int = Field(alias="DATABASE_MAX_OVERFLOW", default=10)


class TwilioSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="TWILIO_", env_file=ENV_FILE, extra="ignore"
    )

    account_sid: str = Field(alias="TWILIO_ACCOUNT_SID")
    auth_token: str = Field(alias="TWILIO_AUTH_TOKEN")
    whatsapp_from: str = Field(alias="TWILIO_WHATSAPP_FROM")
    webhook_verify_token: str = Field(alias="TWILIO_WEBHOOK_VERIFY_TOKEN", default="")
    base_url: AnyHttpUrl = Field(
        alias="TWILIO_BASE_URL", default="https://localhost:8000"
    )

    welcome_template_sid: str = Field(alias="TWILIO_WELCOME_TEMPLATE_SID", default="")
    menu_template_sid: str = Field(alias="TWILIO_MENU_TEMPLATE_SID", default="")
    subscription_template_sid: str = Field(
        alias="TWILIO_SUBSCRIPTION_TEMPLATE_SID", default=""
    )
    daily_fact_template_sid: str = Field(alias="TWILIO_DAILY_FACT_TEMPLATE_SID", default="")
    help_template_sid: str = Field(alias="TWILIO_HELP_TEMPLATE_SID", default="")

    @property
    def webhook_url(self) -> str:
        """Generate the webhook URL dynamically."""
        return f"{str(self.base_url).rstrip('/')}/webhook/whatsapp"

    @property
    def status_callback_url(self) -> str:
        """Generate the status callback URL dynamically."""
        return f"{str(self.base_url).rstrip('/')}/webhook/whatsapp/status"

    @property
    def is_sandbox(self) -> bool:
        """Check if using Twilio WhatsApp Sandbox."""
        return self.whatsapp_from == "whatsapp:+14155238886"

    @property
    def has_templates(self) -> bool:
        """Check if template SIDs are configured."""
        return bool(self.welcome_template_sid and self.menu_template_sid)


class OpenRouterSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENROUTER_", env_file=ENV_FILE, extra="ignore"
    )

    api_key: str = Field(alias="OPENROUTER_API_KEY")
    model: str = Field(alias="OPENROUTER_MODEL", default="openai/gpt-4o-mini")
    base_url: str = Field(
        alias="OPENROUTER_BASE_URL", default="https://openrouter.ai/api/v1"
    )
    max_tokens: int = Field(alias="OPENROUTER_MAX_TOKENS", default=150)
    temperature: float = Field(alias="OPENROUTER_TEMPERATURE", default=0.7)


class WikipediaSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="WIKIPEDIA_", env_file=ENV_FILE, extra="ignore"
    )

    user_agent: str = Field(alias="WIKIPEDIA_USER_AGENT", default="WikiFactsBot/1.0")
    timeout: int = Field(alias="WIKIPEDIA_TIMEOUT", default=10)


class SchedulerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SCHEDULER_", env_file=ENV_FILE, extra="ignore"
    )

    fact_generation_hour: int = Field(alias="SCHEDULER_FACT_GENERATION_HOUR", default=9)
    fact_generation_minute: int = Field(
        alias="SCHEDULER_FACT_GENERATION_MINUTE", default=0
    )
    timezone: str = Field(alias="SCHEDULER_TIMEZONE", default="UTC")


class ServerSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="SERVER_", env_file=ENV_FILE, extra="ignore"
    )

    host: str = Field(alias="SERVER_HOST", default="0.0.0.0")
    port: int = Field(alias="SERVER_PORT", default=8000)
    reload: bool = Field(alias="SERVER_RELOAD", default=False)
    log_level: str = Field(alias="SERVER_LOG_LEVEL", default="info")


class LoggingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LOG_", env_file=ENV_FILE, extra="ignore"
    )

    level: str = Field(alias="LOG_LEVEL", default="INFO")
    format: str = Field(alias="LOG_FORMAT", default="console")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    env_id: Environment = Field(validation_alias="ENV_ID", default=Environment.LOCAL)

    database: DatabaseSettings = DatabaseSettings()
    twilio: TwilioSettings = TwilioSettings()
    openrouter: OpenRouterSettings = OpenRouterSettings()
    wikipedia: WikipediaSettings = WikipediaSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    server: ServerSettings = ServerSettings()
    logging: LoggingSettings = LoggingSettings()


settings = Settings()
