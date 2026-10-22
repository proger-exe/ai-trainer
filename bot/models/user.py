"""
Модели пользователя
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class User(BaseModel):
    """Модель пользователя"""

    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: bool = True
    onboarding_completed: bool = False
    has_grade: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    """Модель для создания пользователя"""

    user_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


class UserUpdate(BaseModel):
    """Модель для обновления пользователя"""

    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    onboarding_completed: Optional[bool] = None
    has_grade: Optional[bool] = None


class UserStats(BaseModel):
    """Статистика пользователя"""

    user_id: int
    total_points: int
    completed_lessons: int
    total_lessons: int
    toxic_sessions: int
    has_grade: bool
    onboarding_completed: bool
