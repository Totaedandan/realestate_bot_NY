from __future__ import annotations

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # Optional admin user id (who can run debug/admin commands).
    # If not set, admin commands are available to everyone.
    ADMIN_USER_ID: int | None = None

    # Chat where leads should be sent (group/channel/private chat id).
    LEADS_CHAT_ID: int | None = None

    # Backward compatibility: old env name
    MANAGER_CHAT_ID: int | None = None

    # Storage
    SQLITE_PATH: str = "./data/bot.sqlite3"

    # Behavior
    LLM_MODE: str = "off"  # off | on
    ENABLE_VOICE: int = 0
    REMINDER_MINUTES: int = 15  # 0 disables reminders

    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-4.1-mini"
    OPENAI_TRANSCRIBE_MODEL: str = "gpt-4o-mini-transcribe"

    @model_validator(mode="after")
    def _finalize(self):
        # If LEADS_CHAT_ID is not provided, fall back to MANAGER_CHAT_ID for old .env files
        if self.LEADS_CHAT_ID is None:
            if self.MANAGER_CHAT_ID is None:
                raise ValueError("Set LEADS_CHAT_ID (or MANAGER_CHAT_ID for backward compatibility).")
            self.LEADS_CHAT_ID = self.MANAGER_CHAT_ID
        return self


settings = Settings()
