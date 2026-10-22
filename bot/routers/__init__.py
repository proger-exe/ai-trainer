"""
Роутеры для группировки обработчиков
"""

from aiogram import Dispatcher
from bot.handlers import common, analysis, toxic, onboarding, leaderboard, learning
from bot.handlers import onboarding_extended, toxic_extended, insight, webapp
from bot.handlers.admin_panel import router as admin_router
from bot.handlers.admin.lessons import router as admin_lessons_router
from bot.handlers.admin.onboarding import router as admin_onboarding_router


def setup_routers(dp: Dispatcher):
    """Настройка всех роутеров"""
    # WebApp обработчик должен быть первым для приёма данных из теста
    dp.include_router(webapp.router)

    dp.include_router(common.router)
    dp.include_router(analysis.router)

    # Расширенные обработчики (должны быть перед базовыми для приоритета)
    dp.include_router(toxic_extended.router)
    dp.include_router(onboarding_extended.router)
    dp.include_router(insight.router)

    # Базовые обработчики
    dp.include_router(toxic.router)
    dp.include_router(learning.router)
    dp.include_router(onboarding.router)
    dp.include_router(leaderboard.router)

    # Админ-панель
    dp.include_router(admin_router)
    dp.include_router(admin_lessons_router)
    dp.include_router(admin_onboarding_router)
