"""
Repository для работы с вопросами онбординга
"""

import aiosqlite
import json
from typing import Optional, List
from datetime import datetime
from bot.repositories.base import BaseRepository
from bot.models.onboarding import (
    OnboardingQuestion,
    OnboardingQuestionCreate,
    OnboardingQuestionUpdate,
)
from core.database import AsyncDatabase


class OnboardingQuestionRepository(BaseRepository[OnboardingQuestion]):
    """Repository для работы с вопросами онбординга"""

    async def create(self, question: OnboardingQuestionCreate) -> OnboardingQuestion:
        """Создание вопроса"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO onboarding_questions 
                (question_key, title, content, options, "order", is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    question.question_key,
                    question.title,
                    question.content,
                    json.dumps(question.options, ensure_ascii=False),
                    question.order,
                    1 if question.is_active else 0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()
            question_id = cursor.lastrowid

        return await self.get_by_id(question_id)

    async def get_by_id(self, question_id: int) -> Optional[OnboardingQuestion]:
        """Получение вопроса по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM onboarding_questions WHERE id = ?", (question_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data["options"] = json.loads(data["options"])
                    data["is_active"] = bool(data["is_active"])
                    return OnboardingQuestion(**data)
        return None

    async def get_by_key(self, question_key: str) -> Optional[OnboardingQuestion]:
        """Получение вопроса по ключу"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM onboarding_questions WHERE question_key = ?",
                (question_key,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    data = dict(row)
                    data["options"] = json.loads(data["options"])
                    data["is_active"] = bool(data["is_active"])
                    return OnboardingQuestion(**data)
        return None

    async def get_all(self, include_inactive: bool = False) -> List[OnboardingQuestion]:
        """Получение всех вопросов"""
        query = "SELECT * FROM onboarding_questions"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += ' ORDER BY "order" ASC'

        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                questions = []
                for row in rows:
                    data = dict(row)
                    data["options"] = json.loads(data["options"])
                    data["is_active"] = bool(data["is_active"])
                    questions.append(OnboardingQuestion(**data))
        return questions

    async def update(
        self, question_id: int, question: OnboardingQuestionUpdate
    ) -> Optional[OnboardingQuestion]:
        """Обновление вопроса"""
        updates = []
        params = []

        if question.question_key is not None:
            updates.append("question_key = ?")
            params.append(question.question_key)
        if question.title is not None:
            updates.append("title = ?")
            params.append(question.title)
        if question.content is not None:
            updates.append("content = ?")
            params.append(question.content)
        if question.options is not None:
            updates.append("options = ?")
            params.append(json.dumps(question.options, ensure_ascii=False))
        if question.order is not None:
            updates.append('"order" = ?')
            params.append(question.order)
        if question.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if question.is_active else 0)

        if not updates:
            return await self.get_by_id(question_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(question_id)

        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute(
                f"UPDATE onboarding_questions SET {', '.join(updates)} WHERE id = ?",
                tuple(params),
            )
            await conn.commit()

        return await self.get_by_id(question_id)

    async def delete(self, question_id: int) -> bool:
        """Удаление вопроса"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                "DELETE FROM onboarding_questions WHERE id = ?", (question_id,)
            )
            await conn.commit()
            return cursor.rowcount > 0

    async def reorder(self, question_id: int, new_order: int) -> bool:
        """Изменение порядка вопроса"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute(
                'UPDATE onboarding_questions SET "order" = ?, updated_at = ? WHERE id = ?',
                (new_order, datetime.now().isoformat(), question_id),
            )
            await conn.commit()
            return True
