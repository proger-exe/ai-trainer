"""
Repository для работы с блоками, уроками и фрагментами
"""

import aiosqlite
from typing import Optional, List
from datetime import datetime
from bot.repositories.base import BaseRepository
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
)


class BlockRepository(BaseRepository[Block]):
    """Repository для работы с блоками"""

    async def create(self, block: BlockCreate) -> Block:
        """Создание блока"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO blocks (title, emoji, description, "order", is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    block.title,
                    block.emoji,
                    block.description,
                    block.order,
                    1 if block.is_active else 0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()
            block_id = cursor.lastrowid

        return await self.get_by_id(block_id)

    async def get_by_id(
        self, block_id: int, include_lessons: bool = False
    ) -> Optional[Block]:
        """Получение блока по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM blocks WHERE id = ?
            """,
                (block_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                block_dict = dict(row)
                block = Block(**block_dict)

                if include_lessons:
                    lesson_repo = LessonRepository(self.db)
                    block.lessons = await lesson_repo.get_by_block_id(
                        block_id, include_fragments=True
                    )

                return block

    async def get_all(self, include_inactive: bool = False) -> List[Block]:
        """Получение всех блоков"""
        query = "SELECT * FROM blocks"
        if not include_inactive:
            query += " WHERE is_active = 1"
        query += ' ORDER BY "order"'

        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(query) as cursor:
                rows = await cursor.fetchall()
                return [Block(**dict(row)) for row in rows]

    async def update(self, block_id: int, block: BlockUpdate) -> Optional[Block]:
        """Обновление блока"""
        updates = []
        params = []

        if block.title is not None:
            updates.append("title = ?")
            params.append(block.title)
        if block.emoji is not None:
            updates.append("emoji = ?")
            params.append(block.emoji)
        if block.description is not None:
            updates.append("description = ?")
            params.append(block.description)
        if block.order is not None:
            updates.append('"order" = ?')
            params.append(block.order)
        if block.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if block.is_active else 0)

        if not updates:
            return await self.get_by_id(block_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(block_id)

        await self.execute_update(
            f"UPDATE blocks SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )

        return await self.get_by_id(block_id)

    async def delete(self, block_id: int) -> bool:
        """Удаление блока"""
        result = await self.execute_update(
            "DELETE FROM blocks WHERE id = ?", (block_id,)
        )
        return result > 0


class LessonRepository(BaseRepository[Lesson]):
    """Repository для работы с уроками"""

    async def create(self, lesson: LessonCreate) -> Lesson:
        """Создание урока"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO lessons (block_id, title, "order", is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    lesson.block_id,
                    lesson.title,
                    lesson.order,
                    1 if lesson.is_active else 0,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()
            lesson_id = cursor.lastrowid

        return await self.get_by_id(lesson_id)

    async def get_by_id(
        self, lesson_id: int, include_fragments: bool = False
    ) -> Optional[Lesson]:
        """Получение урока по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM lessons WHERE id = ?
            """,
                (lesson_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                lesson_dict = dict(row)
                lesson = Lesson(**lesson_dict)

                if include_fragments:
                    fragment_repo = FragmentRepository(self.db)
                    lesson.fragments = await fragment_repo.get_by_lesson_id(lesson_id)

                return lesson

    async def get_by_block_id(
        self, block_id: int, include_fragments: bool = False
    ) -> List[Lesson]:
        """Получение всех уроков блока"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM lessons WHERE block_id = ? ORDER BY "order"
            """,
                (block_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                lessons = [Lesson(**dict(row)) for row in rows]

                if include_fragments:
                    fragment_repo = FragmentRepository(self.db)
                    for lesson in lessons:
                        lesson.fragments = await fragment_repo.get_by_lesson_id(
                            lesson.id
                        )

                return lessons

    async def update(self, lesson_id: int, lesson: LessonUpdate) -> Optional[Lesson]:
        """Обновление урока"""
        updates = []
        params = []

        if lesson.title is not None:
            updates.append("title = ?")
            params.append(lesson.title)
        if lesson.order is not None:
            updates.append('"order" = ?')
            params.append(lesson.order)
        if lesson.is_active is not None:
            updates.append("is_active = ?")
            params.append(1 if lesson.is_active else 0)

        if not updates:
            return await self.get_by_id(lesson_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(lesson_id)

        await self.execute_update(
            f"UPDATE lessons SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )

        return await self.get_by_id(lesson_id)

    async def delete(self, lesson_id: int) -> bool:
        """Удаление урока"""
        result = await self.execute_update(
            "DELETE FROM lessons WHERE id = ?", (lesson_id,)
        )
        return result > 0


class FragmentRepository(BaseRepository[Fragment]):
    """Repository для работы с фрагментами"""

    async def create(self, fragment: FragmentCreate) -> Fragment:
        """Создание фрагмента"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            cursor = await conn.execute(
                """
                INSERT INTO fragments (lesson_id, fragment_type, content, correct_answer, "order", created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    fragment.lesson_id,
                    fragment.fragment_type.value,
                    fragment.content,
                    fragment.correct_answer,
                    fragment.order,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()
            fragment_id = cursor.lastrowid

        return await self.get_by_id(fragment_id)

    async def get_by_id(self, fragment_id: int) -> Optional[Fragment]:
        """Получение фрагмента по ID"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM fragments WHERE id = ?
            """,
                (fragment_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                fragment_dict = dict(row)
                fragment_dict["fragment_type"] = FragmentType(
                    fragment_dict["fragment_type"]
                )
                return Fragment(**fragment_dict)

    async def get_by_lesson_id(self, lesson_id: int) -> List[Fragment]:
        """Получение всех фрагментов урока"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM fragments WHERE lesson_id = ? ORDER BY "order"
            """,
                (lesson_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                fragments = []
                for row in rows:
                    fragment_dict = dict(row)
                    fragment_dict["fragment_type"] = FragmentType(
                        fragment_dict["fragment_type"]
                    )
                    fragments.append(Fragment(**fragment_dict))
                return fragments

    async def update(
        self, fragment_id: int, fragment: FragmentUpdate
    ) -> Optional[Fragment]:
        """Обновление фрагмента"""
        updates = []
        params = []

        if fragment.fragment_type is not None:
            updates.append("fragment_type = ?")
            params.append(fragment.fragment_type.value)
        if fragment.content is not None:
            updates.append("content = ?")
            params.append(fragment.content)
        if fragment.correct_answer is not None:
            updates.append("correct_answer = ?")
            params.append(fragment.correct_answer)
        if fragment.order is not None:
            updates.append('"order" = ?')
            params.append(fragment.order)

        if not updates:
            return await self.get_by_id(fragment_id)

        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(fragment_id)

        await self.execute_update(
            f"UPDATE fragments SET {', '.join(updates)} WHERE id = ?", tuple(params)
        )

        return await self.get_by_id(fragment_id)

    async def delete(self, fragment_id: int) -> bool:
        """Удаление фрагмента"""
        result = await self.execute_update(
            "DELETE FROM fragments WHERE id = ?", (fragment_id,)
        )
        return result > 0

    async def get_next_fragment(
        self, lesson_id: int, current_order: int
    ) -> Optional[Fragment]:
        """Получение следующего фрагмента после текущего"""
        async with aiosqlite.connect(self.db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM fragments 
                WHERE lesson_id = ? AND "order" > ?
                ORDER BY "order" 
                LIMIT 1
            """,
                (lesson_id, current_order),
            ) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return None

                fragment_dict = dict(row)
                fragment_dict["fragment_type"] = FragmentType(
                    fragment_dict["fragment_type"]
                )
                return Fragment(**fragment_dict)
