"""
Конфигурация приложения
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Класс для хранения конфигурации"""

    # Telegram Bot Token
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    # Gemini API Token
    GEMINI_API_TOKEN = os.getenv("GEMINI_API_TOKEN")

    # Admin IDs (можно указать несколько через запятую в .env)
    ADMIN_IDS = [
        int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()
    ]

    # Database path
    DATABASE_PATH = os.getenv("DATABASE_PATH", "bot.db")

    # Models configuration
    MODELS_PATH = os.getenv("MODELS_PATH", "models.json")
    SYNTAX_PATH = os.getenv("SYNTAX_PATH", "syntax.json")

    # Network chat link
    NETWORK_CHAT_LINK = os.getenv("NETWORK_CHAT_LINK", "https://t.me/your_network_chat")

    # WebApp URL for onboarding test (15 questions)
    ONBOARDING_WEBAPP_URL = os.getenv("ONBOARDING_WEBAPP_URL", "")

    @classmethod
    def validate(cls) -> bool:
        """Проверка наличия обязательных токенов"""
        if not cls.TELEGRAM_BOT_TOKEN:
            return False
        if not cls.GEMINI_API_TOKEN:
            return False
        return True
