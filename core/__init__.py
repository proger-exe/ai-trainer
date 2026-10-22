"""
Core модули - общие компоненты для bot и atlant
"""

from core.config import Config
from core.database import AsyncDatabase, Database  # Database для обратной совместимости
from core.bridge import Bridge

__all__ = ["Config", "Database", "Bridge"]
