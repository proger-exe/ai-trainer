"""
Утилиты для валидации данных
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def validate_user_id(user_id: Optional[int]) -> int:
    """
    Валидация user_id

    Args:
        user_id: ID пользователя для проверки

    Returns:
        Валидный user_id

    Raises:
        ValueError: Если user_id невалидный
    """
    if user_id is None:
        raise ValueError("user_id cannot be None")

    if not isinstance(user_id, int):
        raise ValueError(f"user_id must be int, got {type(user_id)}")

    if user_id <= 0:
        raise ValueError(f"user_id must be positive, got {user_id}")

    return user_id


def validate_not_none(value: Optional[any], name: str = "value") -> any:
    """
    Проверка, что значение не None

    Args:
        value: Значение для проверки
        name: Имя переменной для сообщения об ошибке

    Returns:
        Значение, если оно не None

    Raises:
        ValueError: Если значение None
    """
    if value is None:
        raise ValueError(f"{name} cannot be None")
    return value
