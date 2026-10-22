"""
Middleware для бота
"""

from bot.middleware.auth import AdminMiddleware
from bot.middleware.logging import LoggingMiddleware

__all__ = [
    "AdminMiddleware",
    "LoggingMiddleware",
]
