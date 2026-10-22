"""
Сервис для работы с уроками и фрагментами
"""

from typing import Optional, List
from bot.repositories.lesson import (
    BlockRepository,
    LessonRepository,
    FragmentRepository,
)
from bot.models.lesson import (
    Block,
    BlockCreate,
    BlockUpdate,
    Lesson,
    LessonCreate,
    LessonUpdate,
    Fragment,
    FragmentCreate,
    FragmentUpdate,
    FragmentType,
    LessonProgress,
)
from bot.repositories.points import PointsRepository
from core.database import PointsConfig
import aiosqlite
from datetime import datetime


class LessonService:
    """Сервис для работы с уроками"""

    def __init__(
        self,
        block_repo: BlockRepository,
        lesson_repo: LessonRepository,
        fragment_repo: FragmentRepository,
        points_repo: PointsRepository,
    ):
        self.block_repo = block_repo
        self.lesson_repo = lesson_repo
        self.fragment_repo = fragment_repo
        self.points_repo = points_repo

    # ==================== БЛОКИ ====================

    async def create_block(self, block: BlockCreate) -> Block:
        """Создание блока"""
        return await self.block_repo.create(block)

    async def get_block(
        self, block_id: int, include_lessons: bool = False
    ) -> Optional[Block]:
        """Получение блока"""
        return await self.block_repo.get_by_id(
            block_id, include_lessons=include_lessons
        )

    async def get_all_blocks(self, include_inactive: bool = False) -> List[Block]:
        """Получение всех блоков"""
        return await self.block_repo.get_all(include_inactive=include_inactive)

    async def update_block(self, block_id: int, block: BlockUpdate) -> Optional[Block]:
        """Обновление блока"""
        return await self.block_repo.update(block_id, block)

    async def delete_block(self, block_id: int) -> bool:
        """Удаление блока"""
        return await self.block_repo.delete(block_id)

    # ==================== УРОКИ ====================

    async def create_lesson(self, lesson: LessonCreate) -> Lesson:
        """Создание урока"""
        return await self.lesson_repo.create(lesson)

    async def get_lesson(
        self, lesson_id: int, include_fragments: bool = False
    ) -> Optional[Lesson]:
        """Получение урока"""
        return await self.lesson_repo.get_by_id(
            lesson_id, include_fragments=include_fragments
        )

    async def get_lessons_by_block(self, block_id: int) -> List[Lesson]:
        """Получение уроков блока"""
        return await self.lesson_repo.get_by_block_id(block_id, include_fragments=True)

    async def update_lesson(
        self, lesson_id: int, lesson: LessonUpdate
    ) -> Optional[Lesson]:
        """Обновление урока"""
        return await self.lesson_repo.update(lesson_id, lesson)

    async def delete_lesson(self, lesson_id: int) -> bool:
        """Удаление урока"""
        return await self.lesson_repo.delete(lesson_id)

    # ==================== ФРАГМЕНТЫ ====================

    async def create_fragment(self, fragment: FragmentCreate) -> Fragment:
        """Создание фрагмента"""
        return await self.fragment_repo.create(fragment)

    async def get_fragment(self, fragment_id: int) -> Optional[Fragment]:
        """Получение фрагмента"""
        return await self.fragment_repo.get_by_id(fragment_id)

    async def get_fragments_by_lesson(self, lesson_id: int) -> List[Fragment]:
        """Получение фрагментов урока"""
        return await self.fragment_repo.get_by_lesson_id(lesson_id)

    async def update_fragment(
        self, fragment_id: int, fragment: FragmentUpdate
    ) -> Optional[Fragment]:
        """Обновление фрагмента"""
        return await self.fragment_repo.update(fragment_id, fragment)

    async def delete_fragment(self, fragment_id: int) -> bool:
        """Удаление фрагмента"""
        return await self.fragment_repo.delete(fragment_id)

    async def get_next_fragment(
        self, lesson_id: int, current_order: int
    ) -> Optional[Fragment]:
        """Получение следующего фрагмента"""
        return await self.fragment_repo.get_next_fragment(lesson_id, current_order)

    # ==================== ПРОГРЕСС ====================

    async def get_progress(
        self, user_id: int, lesson_id: int
    ) -> Optional[LessonProgress]:
        """Получение прогресса пользователя по уроку"""
        async with aiosqlite.connect(self.fragment_repo.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT fragment_id, completed, updated_at FROM user_fragment_progress 
                WHERE user_id = ? AND lesson_id = ?
            """,
                (user_id, lesson_id),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                # Проверяем наличие updated_at (используем его как completed_at если урок завершен)
                completed_at = None
                try:
                    if row["completed"] and row["updated_at"]:
                        completed_at = datetime.fromisoformat(row["updated_at"])
                except (KeyError, ValueError, TypeError, IndexError):
                    completed_at = None

                return LessonProgress(
                    user_id=user_id,
                    lesson_id=lesson_id,
                    current_fragment_id=row["fragment_id"],
                    completed=bool(row["completed"]),
                    completed_at=completed_at,
                )

    async def save_progress(
        self,
        user_id: int,
        lesson_id: int,
        fragment_id: Optional[int] = None,
        completed: bool = False,
    ) -> bool:
        """Сохранение прогресса пользователя"""
        async with aiosqlite.connect(self.fragment_repo.db.db_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO user_fragment_progress 
                (user_id, lesson_id, fragment_id, completed, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    lesson_id,
                    fragment_id,
                    1 if completed else 0,
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()
            return True

    async def check_test_answer(self, fragment_id: int, user_answer: str) -> bool:
        """Проверка правильности ответа на тест

        Принимает вариант ответа (A, B, C, D или 1, 2, 3).
        В БД хранится только ID правильного ответа.
        """
        import json

        fragment = await self.get_fragment(fragment_id)
        if not fragment or fragment.fragment_type != FragmentType.TEST:
            return False

        if not fragment.correct_answer:
            return False

        user_answer = user_answer.strip().upper()

        # Пытаемся распарсить как JSON (если есть словарь с correct_id)
        try:
            answer_data = json.loads(fragment.correct_answer)
            if isinstance(answer_data, dict) and "correct_id" in answer_data:
                correct_id = str(answer_data.get("correct_id", "")).strip().upper()
                # Простое сравнение ID
                return user_answer == correct_id
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass

        # Если не JSON, значит просто ID (C, 3 и т.д.)
        correct_id = fragment.correct_answer.strip().upper()
        return user_answer == correct_id

    async def validate_fragment_structure(
        self, lesson_id: int
    ) -> tuple[bool, Optional[str]]:
        """Проверка правильности структуры фрагментов урока

        Возвращает (is_valid, error_message)
        Тест должен быть между двумя theory фрагментами
        """
        fragments = await self.get_fragments_by_lesson(lesson_id)
        if not fragments:
            return True, None

        sorted_fragments = sorted(fragments, key=lambda x: x.order)

        # Проверяем каждый тест
        for i, fragment in enumerate(sorted_fragments):
            if fragment.fragment_type == FragmentType.TEST:
                # Тест не может быть первым или последним
                if i == 0 or i == len(sorted_fragments) - 1:
                    return (
                        False,
                        f"Тест на позиции {i + 1} должен быть между двумя фрагментами теории",
                    )

                # Проверяем, что до и после теста есть theory
                prev_fragment = sorted_fragments[i - 1]
                next_fragment = sorted_fragments[i + 1]

                if prev_fragment.fragment_type != FragmentType.THEORY:
                    return (
                        False,
                        f"Перед тестом на позиции {i + 1} должен быть фрагмент теории",
                    )

                if next_fragment.fragment_type != FragmentType.THEORY:
                    return (
                        False,
                        f"После теста на позиции {i + 1} должен быть фрагмент теории",
                    )

        return True, None

    async def mark_test_passed(
        self, user_id: int, lesson_id: int, fragment_id: int
    ) -> bool:
        """Отметить тест как пройденный - сохранить прогресс с указанием следующего фрагмента"""
        lesson = await self.get_lesson(lesson_id, include_fragments=True)
        if not lesson or not lesson.fragments:
            return False

        fragments = sorted(lesson.fragments, key=lambda x: x.order)
        test_fragment = next((f for f in fragments if f.id == fragment_id), None)

        if not test_fragment:
            return False

        # Находим следующий фрагмент после теста
        next_fragment = None
        for i, f in enumerate(fragments):
            if f.id == fragment_id and i + 1 < len(fragments):
                next_fragment = fragments[i + 1]
                break

        # Сохраняем прогресс с указанием следующего фрагмента
        await self.save_progress(
            user_id,
            lesson_id,
            fragment_id=next_fragment.id if next_fragment else fragment_id,
        )
        return True

    async def complete_lesson(self, user_id: int, lesson_id: int) -> bool:
        """Завершение урока и начисление баллов"""
        # Сохраняем прогресс
        await self.save_progress(user_id, lesson_id, completed=True)

        # Начисляем баллы через repository
        await self.points_repo.create(
            user_id=user_id,
            points=PointsConfig.LESSON_COMPLETE,
            source="lesson",
            source_id=str(lesson_id),
            description=f"Урок {lesson_id}",
        )

        return True

    async def get_completed_count(self, user_id: int) -> int:
        """Получение количества пройденных уроков"""
        async with aiosqlite.connect(self.fragment_repo.db.db_path) as conn:
            async with conn.execute(
                """
                SELECT COUNT(*) FROM user_fragment_progress 
                WHERE user_id = ? AND completed = 1
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_total_lessons_count(self) -> int:
        """Получение общего количества уроков"""
        async with aiosqlite.connect(self.fragment_repo.db.db_path) as conn:
            async with conn.execute(
                """
                SELECT COUNT(*) FROM lessons WHERE is_active = 1
            """
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
