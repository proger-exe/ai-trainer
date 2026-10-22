"""
Repository для системы баллов
"""

from typing import Optional, List, Dict
from datetime import datetime
import aiosqlite
from bot.repositories.base import BaseRepository
from bot.models.points import PointsTransaction, PointsBreakdown
from core.database import AsyncDatabase


class PointsRepository(BaseRepository[PointsTransaction]):
    """Repository для работы с баллами"""

    async def create(
        self,
        user_id: int,
        points: int,
        source: str,
        source_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> PointsTransaction:
        """Создание транзакции баллов"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO user_points (user_id, points, source, source_id, description)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, points, source, source_id, description),
            )
            await conn.commit()
            transaction_id = cursor.lastrowid

        return await self.get_by_id(transaction_id)

    async def get_by_id(self, transaction_id: int) -> Optional[PointsTransaction]:
        """Получение транзакции по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM user_points WHERE id = ?", (transaction_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return PointsTransaction(**dict(row))
        return None

    async def get_user_transactions(
        self, user_id: int, limit: Optional[int] = None
    ) -> List[PointsTransaction]:
        """Получение транзакций пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            query = (
                "SELECT * FROM user_points WHERE user_id = ? ORDER BY created_at DESC"
            )
            if limit:
                query += f" LIMIT {limit}"

            async with conn.execute(query, (user_id,)) as cursor:
                rows = await cursor.fetchall()
                return [PointsTransaction(**dict(row)) for row in rows]

    async def get_total_points(self, user_id: int) -> int:
        """Получение общего количества баллов пользователя"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            async with conn.execute(
                """
                SELECT COALESCE(SUM(points), 0) FROM user_points WHERE user_id = ?
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_breakdown(self, user_id: int) -> PointsBreakdown:
        """Получение разбивки баллов по источникам"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            async with conn.execute(
                """
                SELECT source, SUM(points) as total FROM user_points 
                WHERE user_id = ? GROUP BY source
            """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                by_source = {row[0]: row[1] for row in rows}
                total = sum(by_source.values())

                return PointsBreakdown(total=total, by_source=by_source)

    async def get_leaderboard(self, limit: int = 10) -> List[Dict[str, any]]:
        """Получение лидерборда пользователей"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT 
                    user_id,
                    SUM(points) as total_points,
                    COUNT(*) as transactions_count
                FROM user_points
                GROUP BY user_id
                ORDER BY total_points DESC
                LIMIT ?
            """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
