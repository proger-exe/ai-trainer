"""
Repository для пользователей
"""

import aiosqlite
from typing import Optional, List
from datetime import datetime
from bot.repositories.base import BaseRepository
from bot.models.user import User, UserCreate, UserUpdate
from core.database import AsyncDatabase


class UserRepository(BaseRepository[User]):
    """Repository для работы с пользователями"""

    async def create(self, user: UserCreate) -> User:
        """Создание пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (
                    user.user_id,
                    user.username,
                    user.first_name,
                    user.last_name,
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()

        return await self.get_by_id(user.user_id)

    async def get_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return User(**dict(row))
        return None

    async def get_all(self, limit: Optional[int] = None, offset: int = 0) -> List[User]:
        """Получение всех пользователей"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            query = "SELECT * FROM users ORDER BY created_at DESC"
            if limit:
                query += f" LIMIT {limit} OFFSET {offset}"

            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [User(**dict(row)) for row in rows]

    async def update(self, user_id: int, user_update: UserUpdate) -> Optional[User]:
        """Обновление пользователя"""
        updates = []
        params = []

        if user_update.username is not None:
            updates.append("username = ?")
            params.append(user_update.username)
        if user_update.first_name is not None:
            updates.append("first_name = ?")
            params.append(user_update.first_name)
        if user_update.last_name is not None:
            updates.append("last_name = ?")
            params.append(user_update.last_name)
        if user_update.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if user_update.is_active else 0)
        if user_update.onboarding_completed is not None:
            updates.append("onboarding_completed = ?")
            params.append(1 if user_update.onboarding_completed else 0)
        if user_update.has_grade is not None:
            updates.append("has_grade = ?")
            params.append(1 if user_update.has_grade else 0)

        if not updates:
            return await self.get_by_id(user_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(user_id)

        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute(
                f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?",
                tuple(params),
            )
            await conn.commit()

        return await self.get_by_id(user_id)

    async def set_active(self, user_id: int, is_active: bool) -> bool:
        """Установка статуса активности"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            await conn.execute(
                """
                UPDATE users SET is_active = ?, updated_at = ?
                WHERE user_id = ?
            """,
                (1 if is_active else 0, datetime.now().isoformat(), user_id),
            )
            await conn.commit()
            return True

    async def count(self) -> int:
        """Подсчёт количества пользователей"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            async with conn.execute("SELECT COUNT(*) FROM users") as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
