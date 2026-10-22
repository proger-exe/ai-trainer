"""
Сервис для работы с онбордингом
"""

from typing import List, Optional
from bot.repositories.onboarding import OnboardingQuestionRepository
from bot.models.onboarding import (
    OnboardingQuestion,
    OnboardingQuestionCreate,
    OnboardingQuestionUpdate,
)


class OnboardingService:
    """Сервис для работы с онбордингом"""

    def __init__(self, question_repo: OnboardingQuestionRepository):
        self.question_repo = question_repo

    async def create_question(
        self, question: OnboardingQuestionCreate
    ) -> OnboardingQuestion:
        """Создание вопроса"""
        return await self.question_repo.create(question)

    async def get_question(self, question_id: int) -> Optional[OnboardingQuestion]:
        """Получение вопроса по ID"""
        return await self.question_repo.get_by_id(question_id)

    async def get_question_by_key(
        self, question_key: str
    ) -> Optional[OnboardingQuestion]:
        """Получение вопроса по ключу"""
        return await self.question_repo.get_by_key(question_key)

    async def get_all_questions(
        self, include_inactive: bool = False
    ) -> List[OnboardingQuestion]:
        """Получение всех вопросов"""
        return await self.question_repo.get_all(include_inactive=include_inactive)

    async def update_question(
        self, question_id: int, question: OnboardingQuestionUpdate
    ) -> Optional[OnboardingQuestion]:
        """Обновление вопроса"""
        return await self.question_repo.update(question_id, question)

    async def delete_question(self, question_id: int) -> bool:
        """Удаление вопроса"""
        return await self.question_repo.delete(question_id)

    async def reorder_question(self, question_id: int, new_order: int) -> bool:
        """Изменение порядка вопроса"""
        return await self.question_repo.reorder(question_id, new_order)

    async def get_active_questions_ordered(self) -> List[OnboardingQuestion]:
        """Получение активных вопросов в порядке отображения"""
        questions = await self.get_all_questions(include_inactive=False)
        return sorted(questions, key=lambda x: x.order)
