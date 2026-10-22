"""
Модели системы баллов
"""

from pydantic import BaseModel
from typing import Optional, Dict
from datetime import datetime


class PointsTransaction(BaseModel):
    """Транзакция начисления баллов"""

    id: int
    user_id: int
    points: int
    source: str
    source_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PointsBreakdown(BaseModel):
    """Разбивка баллов по источникам"""

    total: int
    by_source: Dict[str, int]

    class Config:
        from_attributes = True


class PointsResult(BaseModel):
    """Результат операции с баллами"""

    user_id: int
    points_added: int
    total_points: int
    grade_achieved: bool = False
    grade_threshold: int = 1000
