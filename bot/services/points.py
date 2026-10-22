"""
Сервис для работы с баллами
"""

from typing import Optional, List
from bot.repositories.points import PointsRepository
from bot.repositories.user import UserRepository
from bot.models.points import PointsResult, PointsBreakdown, PointsTransaction
from core.database import PointsConfig


class PointsService:
    """Сервис для работы с баллами"""

    def __init__(self, points_repo: PointsRepository, user_repo: UserRepository):
        self.points_repo = points_repo
        self.user_repo = user_repo

    async def add_points(
        self,
        user_id: int,
        points: int,
        source: str,
        source_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PointsResult:
        """Добавление баллов пользователю"""
        # Создаём транзакцию
        transaction = await self.points_repo.create(
            user_id=user_id,
            points=points,
            source=source,
            source_id=source_id,
            description=description,
        )

        # Получаем общее количество баллов
        total_points = await self.points_repo.get_total_points(user_id)

        # Проверяем достижение грейда
        grade_achieved = False
        if total_points >= PointsConfig.GRADE_THRESHOLD:
            user = await self.user_repo.get_by_id(user_id)
            if user and not user.has_grade:
                from bot.models.user import UserUpdate

                await self.user_repo.update(user_id, UserUpdate(has_grade=True))
                grade_achieved = True

        return PointsResult(
            user_id=user_id,
            points_added=points,
            total_points=total_points,
            grade_achieved=grade_achieved,
            grade_threshold=PointsConfig.GRADE_THRESHOLD,
        )

    async def get_total_points(self, user_id: int) -> int:
        """Получение общего количества баллов"""
        return await self.points_repo.get_total_points(user_id)

    async def get_breakdown(self, user_id: int) -> PointsBreakdown:
        """Получение разбивки баллов"""
        return await self.points_repo.get_breakdown(user_id)

    async def get_transactions(
        self, user_id: int, limit: Optional[int] = None
    ) -> List[PointsTransaction]:
        """Получение транзакций пользователя"""
        return await self.points_repo.get_user_transactions(user_id, limit)

    async def get_leaderboard(self, limit: int = 10) -> List[dict]:
        """Получение лидерборда"""
        return await self.points_repo.get_leaderboard(limit)
