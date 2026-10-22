"""
Dependency Injection контейнер
"""

from typing import Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from core.database import AsyncDatabase
    from bot.repositories.user import UserRepository
    from bot.repositories.points import PointsRepository
    from bot.repositories.toxic import ToxicRepository
    from bot.repositories.lesson import (
        BlockRepository,
        LessonRepository,
        FragmentRepository,
    )
    from bot.repositories.onboarding import OnboardingQuestionRepository
    from bot.services.user import UserService
    from bot.services.points import PointsService
    from bot.services.toxic import ToxicService
    from bot.services.lesson import LessonService
    from bot.services.onboarding import OnboardingService
else:
    # Ленивые импорты для избежания циклических зависимостей
    AsyncDatabase = None
    UserRepository = None
    PointsRepository = None
    ToxicRepository = None
    BlockRepository = None
    LessonRepository = None
    FragmentRepository = None
    OnboardingQuestionRepository = None
    UserService = None
    PointsService = None
    ToxicService = None
    LessonService = None
    OnboardingService = None


class Container:
    """Контейнер зависимостей"""

    _instance: Optional["Container"] = None
    _db: Optional[AsyncDatabase] = None
    _repositories: Dict[str, Any] = {}
    _services: Dict[str, Any] = {}

    def __init__(self):
        if Container._instance is not None:
            raise RuntimeError("Container is a singleton. Use Container.get_instance()")
        Container._instance = self

    @classmethod
    def get_instance(cls) -> "Container":
        """Получение экземпляра контейнера"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self, db_path: Optional[str] = None):
        """Инициализация контейнера"""
        if self._db is None:
            # Ленивый импорт
            from core.database import AsyncDatabase

            self._db = AsyncDatabase(db_path)
            await self._db.init_db()

    def get_db(self):
        """Получение экземпляра БД"""
        if self._db is None:
            raise RuntimeError("Container not initialized. Call initialize() first.")
        return self._db

    # ==================== REPOSITORIES ====================

    def get_user_repository(self):
        """Получение UserRepository"""
        if "user" not in self._repositories:
            from bot.repositories.user import UserRepository

            self._repositories["user"] = UserRepository(self.get_db())
        return self._repositories["user"]

    def get_points_repository(self):
        """Получение PointsRepository"""
        if "points" not in self._repositories:
            from bot.repositories.points import PointsRepository

            self._repositories["points"] = PointsRepository(self.get_db())
        return self._repositories["points"]

    def get_toxic_repository(self):
        """Получение ToxicRepository"""
        if "toxic" not in self._repositories:
            from bot.repositories.toxic import ToxicRepository

            self._repositories["toxic"] = ToxicRepository(self.get_db())
        return self._repositories["toxic"]

    def get_block_repository(self):
        """Получение BlockRepository"""
        if "block" not in self._repositories:
            from bot.repositories.lesson import BlockRepository

            self._repositories["block"] = BlockRepository(self.get_db())
        return self._repositories["block"]

    def get_lesson_repository(self):
        """Получение LessonRepository"""
        if "lesson" not in self._repositories:
            from bot.repositories.lesson import LessonRepository

            self._repositories["lesson"] = LessonRepository(self.get_db())
        return self._repositories["lesson"]

    def get_fragment_repository(self):
        """Получение FragmentRepository"""
        if "fragment" not in self._repositories:
            from bot.repositories.lesson import FragmentRepository

            self._repositories["fragment"] = FragmentRepository(self.get_db())
        return self._repositories["fragment"]

    def get_onboarding_question_repository(self):
        """Получение OnboardingQuestionRepository"""
        if "onboarding_question" not in self._repositories:
            from bot.repositories.onboarding import OnboardingQuestionRepository

            self._repositories["onboarding_question"] = OnboardingQuestionRepository(
                self.get_db()
            )
        return self._repositories["onboarding_question"]

    # ==================== SERVICES ====================

    def get_points_service(self):
        """Получение PointsService"""
        if "points" not in self._services:
            from bot.services.points import PointsService

            self._services["points"] = PointsService(
                self.get_points_repository(), self.get_user_repository()
            )
        return self._services["points"]

    def get_user_service(self):
        """Получение UserService"""
        if "user" not in self._services:
            from bot.services.user import UserService

            self._services["user"] = UserService(
                self.get_user_repository(),
                self.get_points_repository(),
                self.get_toxic_repository(),
            )
        return self._services["user"]

    def get_toxic_service(self):
        """Получение ToxicService"""
        if "toxic" not in self._services:
            from bot.services.toxic import ToxicService

            self._services["toxic"] = ToxicService(
                self.get_toxic_repository(), self.get_points_service()
            )
        return self._services["toxic"]

    def get_lesson_service(self):
        """Получение LessonService"""
        if "lesson" not in self._services:
            from bot.services.lesson import LessonService

            self._services["lesson"] = LessonService(
                self.get_block_repository(),
                self.get_lesson_repository(),
                self.get_fragment_repository(),
                self.get_points_repository(),
            )
        return self._services["lesson"]

    def get_onboarding_service(self):
        """Получение OnboardingService"""
        if "onboarding" not in self._services:
            from bot.services.onboarding import OnboardingService

            self._services["onboarding"] = OnboardingService(
                self.get_onboarding_question_repository()
            )
        return self._services["onboarding"]

    def reset(self):
        """Сброс контейнера (для тестов)"""
        self._repositories.clear()
        self._services.clear()
        self._db = None
