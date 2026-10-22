"""
Главный файл запуска Telegram-бота "Тренажёр коммуникаций"
"""

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from core.config import Config
from core.database import AsyncDatabase
from core.container import Container
from core.bridge import bridge
from AtlantSDK import Dispatcher as AtlantDispatcher
from bot.routers import setup_routers as setup_bot_routers
from atlant.routers import setup_routers as setup_atlant_routers

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    """Главная функция запуска бота"""

    # Проверка конфигурации
    if not Config.validate():
        logger.error("Не установлены обязательные токены в .env файле")
        logger.error("Требуются: TELEGRAM_BOT_TOKEN, GEMINI_API_TOKEN")
        return

    # Инициализация контейнера зависимостей
    logger.info("Инициализация контейнера зависимостей...")
    container = Container.get_instance()
    await container.initialize(Config.DATABASE_PATH)
    logger.info("Контейнер инициализирован")

    # Инициализация AtlantSDK Dispatcher
    logger.info("Инициализация AtlantSDK...")
    atlant_dp = AtlantDispatcher(
        token=Config.GEMINI_API_TOKEN,
        models_path=Config.MODELS_PATH,
        syntax_path=Config.SYNTAX_PATH,
    )

    # Подключаем роутеры AtlantSDK
    setup_atlant_routers(atlant_dp)

    # Инициализируем модели
    atlant_dp.start_polling(start_command="START", to_model="ANALYSIS")
    logger.info("AtlantSDK инициализирован")

    # Инициализация Telegram бота
    logger.info("Инициализация Telegram бота...")
    bot = Bot(
        token=Config.TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    # Получаем event loop для отправки сообщений из синхронных обработчиков
    loop = asyncio.get_event_loop()

    # Настраиваем bridge для взаимодействия между компонентами
    bridge.set_telegram_bot(bot, loop)
    bridge.set_atlant_dispatcher(atlant_dp)

    # Инициализация aiogram Dispatcher
    dp = Dispatcher(storage=MemoryStorage())

    # Подключаем роутеры Telegram бота
    setup_bot_routers(dp)

    # Инициализация планировщика
    logger.info("Запуск планировщика задач...")
    from bot.services.scheduler import scheduler

    await scheduler.start(bot)

    # Инициализация базовых инсайтов
    logger.info("Инициализация базовых инсайтов...")
    from bot.handlers.insight import init_default_insights

    await init_default_insights()

    # Запуск API сервера для приёма результатов теста с сайта
    logger.info("Запуск API сервера...")
    from api_server import start_api_server

    api_runner = await start_api_server(bot, host="0.0.0.0", port=8080)
    logger.info("API сервер запущен на порту 8080")

    # Запуск Supabase поллера для получения результатов теста
    logger.info("Запуск Supabase поллера...")
    from bot.services.supabase_poller import start_supabase_poller, stop_supabase_poller

    if await start_supabase_poller(bot, poll_interval=2.0):
        logger.info("Supabase поллер запущен (интервал: 2 сек)")

    logger.info("Бот запущен и готов к работе!")
    logger.info("Используется Long Polling")

    # Запуск бота
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        logger.info("Завершение работы бота...")
        await scheduler.stop()
        await stop_supabase_poller()
        if api_runner:
            await api_runner.cleanup()
        await bot.session.close()
        # Graceful shutdown для контейнера
        container.reset()
        logger.info("Бот остановлен")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
