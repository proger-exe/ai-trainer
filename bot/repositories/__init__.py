"""
Repository слой для работы с БД
"""

from bot.repositories.base import BaseRepository
from bot.repositories.user import UserRepository
from bot.repositories.points import PointsRepository
from bot.repositories.toxic import ToxicRepository

__all__ = [
    "BaseRepository",
    "UserRepository",
    "PointsRepository",
    "ToxicRepository",
]
