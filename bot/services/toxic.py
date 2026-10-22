"""
Сервис для работы с Toxic Chat
"""

from typing import Optional, List, Tuple
from bot.repositories.toxic import ToxicRepository
from bot.repositories.user import UserRepository
from bot.services.points import PointsService
from bot.models.toxic import ToxicResult, ToxicStats


class ToxicService:
    """Сервис для работы с Toxic Chat"""

    def __init__(self, toxic_repo: ToxicRepository, points_service: PointsService):
        self.toxic_repo = toxic_repo
        self.points_service = points_service

    async def save_result(
        self,
        user_id: int,
        boundaries_score: int,
        manipulation_score: int,
        negotiation_score: int,
        feedback: str,
        session_id: Optional[int] = None,
    ) -> Tuple[ToxicResult, int]:
        """Сохранение результата сессии и начисление баллов"""
        # Сохраняем результат
        result = await self.toxic_repo.create(
            user_id=user_id,
            boundaries_score=boundaries_score,
            manipulation_score=manipulation_score,
            negotiation_score=negotiation_score,
            feedback=feedback,
            session_id=session_id,
        )

        # Начисляем баллы
        points_result = await self.points_service.add_points(
            user_id=user_id,
            points=result.total_points,
            source="toxic_chat",
            description=f"Toxic Chat: границы={boundaries_score}, манипуляции={manipulation_score}, переговоры={negotiation_score}",
        )

        return result, points_result.total_points

    async def get_user_results(
        self, user_id: int, limit: Optional[int] = None
    ) -> List[ToxicResult]:
        """Получение результатов пользователя"""
        return await self.toxic_repo.get_user_results(user_id, limit)

    async def get_stats(self, user_id: int) -> ToxicStats:
        """Получение статистики пользователя"""
        return await self.toxic_repo.get_stats(user_id)

    async def count_sessions(self, user_id: int) -> int:
        """Подсчёт количества сессий"""
        return await self.toxic_repo.count_sessions(user_id)
