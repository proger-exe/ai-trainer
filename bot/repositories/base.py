"""
Базовый репозиторий
"""

import logging
import aiosqlite
from abc import ABC
from typing import TypeVar, Generic, Optional, List, Dict, Any
from core.database import AsyncDatabase

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Базовый класс для репозиториев"""

    def __init__(self, db: AsyncDatabase):
        self.db = db

    async def execute_query(
        self, query: str, params: tuple = ()
    ) -> List[Dict[str, Any]]:
        """Выполнение запроса с возвратом результатов"""
        try:
            async with aiosqlite.connect(self.db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(query, params) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except aiosqlite.Error as e:
            logger.error(
                f"[Repository] Database error in execute_query: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.exception(f"[Repository] Unexpected error in execute_query: {e}")
            raise

    async def execute_one(
        self, query: str, params: tuple = ()
    ) -> Optional[Dict[str, Any]]:
        """Выполнение запроса с возвратом одного результата"""
        try:
            async with aiosqlite.connect(self.db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(query, params) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except aiosqlite.Error as e:
            logger.error(
                f"[Repository] Database error in execute_one: {e}", exc_info=True
            )
            raise
        except Exception as e:
            logger.exception(f"[Repository] Unexpected error in execute_one: {e}")
            raise

    async def execute_update(self, query: str, params: tuple = ()) -> int:
        """Выполнение UPDATE/INSERT/DELETE запроса"""
        try:
            async with aiosqlite.connect(self.db.db_path) as conn:
                cursor = await conn.execute(query, params)
                await conn.commit()
                return cursor.rowcount
        except aiosqlite.Error as e:
            logger.error(
                f"[Repository] Database error in execute_update: {e}", exc_info=True
            )
            # Откатываем транзакцию при ошибке
            try:
                await conn.rollback()
            except Exception:
                pass
            raise
        except Exception as e:
            logger.exception(f"[Repository] Unexpected error in execute_update: {e}")
            raise
