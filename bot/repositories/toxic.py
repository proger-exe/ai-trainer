"""
Repository для Toxic Chat
"""

from typing import Optional, List
from datetime import datetime
import aiosqlite
from bot.repositories.base import BaseRepository
from bot.models.toxic import ToxicResult, ToxicStats
from core.database import AsyncDatabase


class ToxicRepository(BaseRepository[ToxicResult]):
    """Repository для работы с результатами Toxic Chat"""

    async def create(
        self,
        user_id: int,
        boundaries_score: int,
        manipulation_score: int,
        negotiation_score: int,
        feedback: str,
        session_id: Optional[int] = None,
    ) -> ToxicResult:
        """Создание результата сессии"""
        # Ограничиваем оценки от 1 до 10
        boundaries_score = max(1, min(10, boundaries_score))
        manipulation_score = max(1, min(10, manipulation_score))
        negotiation_score = max(1, min(10, negotiation_score))

        total_points = boundaries_score + manipulation_score + negotiation_score

        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO toxic_results 
                (user_id, session_id, boundaries_score, manipulation_score, negotiation_score, total_points, feedback)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    session_id,
                    boundaries_score,
                    manipulation_score,
                    negotiation_score,
                    total_points,
                    feedback,
                ),
            )
            await conn.commit()
            result_id = cursor.lastrowid

        return await self.get_by_id(result_id)

    async def get_by_id(self, result_id: int) -> Optional[ToxicResult]:
        """Получение результата по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM toxic_results WHERE id = ?", (result_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return ToxicResult(**dict(row))
        return None

    async def get_user_results(
        self, user_id: int, limit: Optional[int] = None
    ) -> List[ToxicResult]:
        """Получение результатов пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            query = (
                "SELECT * FROM toxic_results WHERE user_id = ? ORDER BY created_at DESC"
            )
            if limit:
                query += f" LIMIT {limit}"

            async with conn.execute(query, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [ToxicResult(**dict(row)) for row in rows]

    async def get_stats(self, user_id: int) -> ToxicStats:
        """Получение статистики пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            async with conn.execute(
                """
                SELECT 
                    COUNT(*) as sessions_count,
                    COALESCE(SUM(total_points), 0) as total_points,
                    COALESCE(AVG(boundaries_score), 0) as avg_boundaries,
                    COALESCE(AVG(manipulation_score), 0) as avg_manipulation,
                    COALESCE(AVG(negotiation_score), 0) as avg_negotiation
                FROM toxic_results WHERE user_id = ?
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return ToxicStats(
                    sessions_count=row[0],
                    total_points=row[1],
                    avg_boundaries=round(row[2], 1),
                    avg_manipulation=round(row[3], 1),
                    avg_negotiation=round(row[4], 1),
                )

    async def count_sessions(self, user_id: int) -> int:
        """Подсчёт количества сессий пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            async with conn.execute(
                """
                SELECT COUNT(*) FROM toxic_results WHERE user_id = ?
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0
