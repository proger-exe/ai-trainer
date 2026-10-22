"""
Модели для системы уроков
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from enum import Enum


class FragmentType(str, Enum):
    """Тип фрагмента урока"""

    THEORY = "theory"
    TEST = "test"


class Block(BaseModel):
    """Модель блока обучения"""

    id: int
    title: str
    emoji: str
    description: Optional[str] = None
    order: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    lessons: List["Lesson"] = []

    class Config:
        from_attributes = True


class BlockCreate(BaseModel):
    """Модель для создания блока"""

    title: str
    emoji: str
    description: Optional[str] = None
    order: int
    is_active: bool = True


class BlockUpdate(BaseModel):
    """Модель для обновления блока"""

    title: Optional[str] = None
    emoji: Optional[str] = None
    description: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class Fragment(BaseModel):
    """Модель фрагмента урока"""

    id: int
    lesson_id: int
    fragment_type: FragmentType
    content: str
    correct_answer: Optional[str] = None  # Для фрагментов типа test
    order: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FragmentCreate(BaseModel):
    """Модель для создания фрагмента"""

    lesson_id: int
    fragment_type: FragmentType
    content: str
    correct_answer: Optional[str] = None
    order: int


class FragmentUpdate(BaseModel):
    """Модель для обновления фрагмента"""

    fragment_type: Optional[FragmentType] = None
    content: Optional[str] = None
    correct_answer: Optional[str] = None
    order: Optional[int] = None


class Lesson(BaseModel):
    """Модель урока"""

    id: int
    block_id: int
    title: str
    order: int
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    fragments: List[Fragment] = []

    class Config:
        from_attributes = True


class LessonCreate(BaseModel):
    """Модель для создания урока"""

    block_id: int
    title: str
    order: int
    is_active: bool = True


class LessonUpdate(BaseModel):
    """Модель для обновления урока"""

    title: Optional[str] = None
    order: Optional[int] = None
    is_active: Optional[bool] = None


class LessonProgress(BaseModel):
    """Прогресс прохождения урока пользователем"""

    user_id: int
    lesson_id: int
    current_fragment_id: Optional[int] = (
        None  # Текущий фрагмент, на котором остановился пользователь
    )
    completed: bool = False
    completed_at: Optional[datetime] = None
