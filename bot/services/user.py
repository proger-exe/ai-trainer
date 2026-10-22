"""
Сервис для работы с пользователями
"""

from typing import Optional, List
from bot.repositories.user import UserRepository
from bot.models.user import User, UserCreate, UserUpdate, UserStats
from bot.repositories.points import PointsRepository
from bot.repositories.toxic import ToxicRepository


class UserService:
    """Сервис для работы с пользователями"""

    def __init__(
        self,
        user_repo: UserRepository,
        points_repo: PointsRepository,
        toxic_repo: ToxicRepository,
    ):
        self.user_repo = user_repo
        self.points_repo = points_repo
        self.toxic_repo = toxic_repo

    async def create_or_update_user(self, user: UserCreate) -> User:
        """Создание или обновление пользователя"""
        existing = await self.user_repo.get_by_id(user.user_id)
        if existing:
            # Обновляем только если есть изменения
            update = UserUpdate(
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
            )
            return await self.user_repo.update(user.user_id, update)
        return await self.user_repo.create(user)

    async def get_user(self, user_id: int) -> Optional[User]:
        """Получение пользователя"""
        return await self.user_repo.get_by_id(user_id)

    async def get_user_stats(self, user_id: int) -> Optional[UserStats]:
        """Получение статистики пользователя"""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        total_points = await self.points_repo.get_total_points(user_id)
        toxic_sessions = await self.toxic_repo.count_sessions(user_id)

        return UserStats(
            user_id=user_id,
            total_points=total_points,
            completed_lessons=0,
            total_lessons=0,
            toxic_sessions=toxic_sessions,
            has_grade=user.has_grade,
            onboarding_completed=user.onboarding_completed,
        )

    async def set_active(self, user_id: int, is_active: bool) -> bool:
        """Установка статуса активности"""
        return await self.user_repo.set_active(user_id, is_active)

    async def get_all_users(
        self, limit: Optional[int] = None, offset: int = 0
    ) -> List[User]:
        """Получение всех пользователей"""
        return await self.user_repo.get_all(limit, offset)
