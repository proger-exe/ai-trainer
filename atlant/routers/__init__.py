"""
Роутеры для AtlantSDK моделей
"""

from atlant.handlers.analysis import router as analysis_router
from atlant.handlers.toxic import router as toxic_router


def setup_routers(atlant_dispatcher):
    """Настройка всех роутеров AtlantSDK"""
    atlant_dispatcher.include_routers([analysis_router, toxic_router])
