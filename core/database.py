"""
Асинхронная база данных SQLite для хранения контекста и пользователей
"""

import logging
import aiosqlite
import json
from typing import Optional, Dict, Any, List
from datetime import datetime
from core.config import Config

logger = logging.getLogger(__name__)


# Константы для системы баллов
class PointsConfig:
    """Конфигурация начисления баллов"""

    # Уроки
    LESSON_COMPLETE = 50  # За пройденный урок
    QUIZ_COMPLETE = 10  # Бонус за тест после урока

    # Онбординг (расширенный)
    ONBOARDING_COMPLETE = 50  # Общие баллы за полный онбординг
    ONBOARDING_QUESTIONS = 10  # За прохождение вопросов
    ONBOARDING_DEMO_LEARNING = 10  # За демо обучения
    ONBOARDING_DEMO_TOXIC = 15  # За демо токсик-чата
    ONBOARDING_DEMO_TASKS = 10  # За демо заданий
    ONBOARDING_FINAL = 5  # За завершение

    # Toxic Chat
    TOXIC_MAX_PER_SESSION = 30  # Максимум за сессию
    TOXIC_MISSION_BONUS = 10  # Бонус за миссию

    # Daily Insight
    INSIGHT_VIEW = 15  # За просмотр инсайта
    INSIGHT_STREAK_BONUS = 5  # Бонус за серию (каждые 7 дней)

    # Грейды
    GRADE_THRESHOLD = 1000  # Порог для первого грейда
    GRADE_2_THRESHOLD = 3000  # Порог для второго грейда
    GRADE_3_THRESHOLD = 5000  # Порог для третьего грейда


class AsyncDatabase:
    """Асинхронный класс для работы с базой данных"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH

    def get_connection(self):
        """Получение async context manager для соединения с БД"""
        return aiosqlite.connect(self.db_path)

    async def init_db(self):
        """Инициализация базы данных"""
        async with aiosqlite.connect(self.db_path) as conn:
            # Таблица пользователей
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    is_active INTEGER DEFAULT 1,
                    onboarding_completed INTEGER DEFAULT 0,
                    has_grade INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица блоков обучения
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    emoji TEXT NOT NULL,
                    description TEXT,
                    "order" INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица уроков
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS lessons (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    block_id INTEGER NOT NULL,
                    title TEXT NOT NULL,
                    "order" INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE
                )
            """
            )

            # Таблица фрагментов уроков
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS fragments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER NOT NULL,
                    fragment_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    correct_answer TEXT,
                    "order" INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                )
            """
            )

            # Таблица прогресса по фрагментам
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_fragment_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    lesson_id INTEGER NOT NULL,
                    fragment_id INTEGER,
                    completed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id),
                    FOREIGN KEY (fragment_id) REFERENCES fragments(id),
                    UNIQUE(user_id, lesson_id)
                )
            """
            )

            # Миграция: удаляем старые колонки из lessons, если они есть
            async with conn.execute("PRAGMA table_info(lessons)") as cursor:
                rows = await cursor.fetchall()
                columns = [row[1] for row in rows]
                if "content" in columns:
                    # Создаём временную таблицу без старых колонок
                    await conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS lessons_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            block_id INTEGER NOT NULL,
                            title TEXT NOT NULL,
                            "order" INTEGER DEFAULT 0,
                            is_active INTEGER DEFAULT 1,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (block_id) REFERENCES blocks(id) ON DELETE CASCADE
                        )
                    """
                    )
                    await conn.execute(
                        """
                        INSERT INTO lessons_new (id, block_id, title, "order", is_active, created_at, updated_at)
                        SELECT id, block_id, title, "order", is_active, created_at, updated_at FROM lessons
                    """
                    )
                    await conn.execute("DROP TABLE lessons")
                    await conn.execute("ALTER TABLE lessons_new RENAME TO lessons")
                    await conn.commit()

            # Таблица контекста разбора ситуаций
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    context_data TEXT,
                    goal TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица контекста токсичного собеседника
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS toxic_context (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    context_data TEXT,
                    session_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица истории сообщений
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    module_type TEXT,
                    message_text TEXT,
                    response_text TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица событий для админ-панели
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    event_type TEXT,
                    event_data TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица баллов пользователей
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    points INTEGER DEFAULT 0,
                    source TEXT,
                    source_id TEXT,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица прогресса по урокам (старая, оставляем для совместимости)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_lesson_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    block_id INTEGER,
                    lesson_id INTEGER,
                    completed INTEGER DEFAULT 0,
                    completed_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    UNIQUE(user_id, block_id, lesson_id)
                )
            """
            )

            # Таблица результатов Toxic Chat сессий
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS toxic_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    session_id INTEGER,
                    mode TEXT DEFAULT 'free',
                    scenario TEXT,
                    boundaries_score INTEGER DEFAULT 0,
                    manipulation_score INTEGER DEFAULT 0,
                    negotiation_score INTEGER DEFAULT 0,
                    goal_scores TEXT,
                    total_points INTEGER DEFAULT 0,
                    feedback TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица сессий Toxic Chat (расширенная)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS toxic_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    mode TEXT DEFAULT 'free',
                    scenario TEXT,
                    goals TEXT,
                    mission_id TEXT,
                    is_demo INTEGER DEFAULT 0,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    ended_at TEXT,
                    is_active INTEGER DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица прогресса онбординга (расширенная)
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS onboarding_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    current_phase TEXT DEFAULT 'welcome',
                    current_step INTEGER DEFAULT 0,
                    answers TEXT,
                    demo_learning_done INTEGER DEFAULT 0,
                    demo_toxic_done INTEGER DEFAULT 0,
                    demo_tasks_done INTEGER DEFAULT 0,
                    recommended_block INTEGER,
                    ai_recommendation TEXT,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Таблица вопросов онбординга
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS onboarding_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question_key TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    options TEXT NOT NULL,
                    "order" INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица инсайтов
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tip TEXT NOT NULL,
                    emoji TEXT DEFAULT '💡',
                    is_ai_generated INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            # Таблица просмотренных инсайтов
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_insights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    insight_id INTEGER,
                    insight_date TEXT,
                    viewed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    points_earned INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (insight_id) REFERENCES insights(id),
                    UNIQUE(user_id, insight_date)
                )
            """
            )

            # Таблица вопросов тестов
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_questions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    lesson_id INTEGER NOT NULL,
                    part_index INTEGER,
                    question_text TEXT NOT NULL,
                    question_type TEXT DEFAULT 'single',
                    options TEXT NOT NULL,
                    correct_answers TEXT NOT NULL,
                    explanation TEXT,
                    "order" INTEGER DEFAULT 0,
                    is_active INTEGER DEFAULT 1,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id) ON DELETE CASCADE
                )
            """
            )

            # Добавляем колонку part_index, если она отсутствует (для существующих БД)
            async with conn.execute("PRAGMA table_info(quiz_questions)") as cursor:
                rows = await cursor.fetchall()
                columns = [row[1] for row in rows]
                if "part_index" not in columns:
                    await conn.execute(
                        "ALTER TABLE quiz_questions ADD COLUMN part_index INTEGER"
                    )
                    await conn.commit()

            # Таблица попыток прохождения тестов
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS quiz_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    lesson_id INTEGER,
                    answers TEXT,
                    score INTEGER DEFAULT 0,
                    total_questions INTEGER DEFAULT 0,
                    passed INTEGER DEFAULT 0,
                    attempt_number INTEGER DEFAULT 1,
                    started_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    completed_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id),
                    FOREIGN KEY (lesson_id) REFERENCES lessons(id)
                )
            """
            )

            # Таблица настроек уведомлений пользователей
            await conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE,
                    daily_insight_enabled INTEGER DEFAULT 1,
                    insight_time TEXT DEFAULT '10:00',
                    timezone TEXT DEFAULT 'Europe/Moscow',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """
            )

            # Миграции - добавляем новые колонки если их нет
            try:
                await conn.execute(
                    "ALTER TABLE users ADD COLUMN onboarding_completed INTEGER DEFAULT 0"
                )
            except aiosqlite.OperationalError:
                pass

            try:
                await conn.execute(
                    "ALTER TABLE users ADD COLUMN has_grade INTEGER DEFAULT 0"
                )
            except aiosqlite.OperationalError:
                pass

            await conn.commit()

    # ==================== ПОЛЬЗОВАТЕЛИ ====================

    async def add_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
    ):
        """Добавление или обновление пользователя"""

        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        user_id,
                        username,
                        first_name,
                        last_name,
                        datetime.now().isoformat(),
                    ),
                )
                await conn.commit()
        except aiosqlite.Error as e:
            logger.error(f"[Database] Error adding user {user_id}: {e}", exc_info=True)
            raise
        except Exception as e:
            logger.exception(f"[Database] Unexpected error adding user {user_id}: {e}")
            raise

    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return dict(row)
        return None

    async def set_user_active(self, user_id: int, is_active: bool):
        """Установка статуса активности пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE users SET is_active = ?, updated_at = ?
                WHERE user_id = ?
            """,
                (1 if is_active else 0, datetime.now().isoformat(), user_id),
            )
            await conn.commit()

    async def get_all_users(self) -> List[Dict[str, Any]]:
        """Получение списка всех пользователей"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM users ORDER BY created_at DESC"
            ) as cursor:
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]

    # ==================== КОНТЕКСТЫ ====================

    async def save_analysis_context(
        self, user_id: int, context_data: Dict[str, Any], goal: Optional[str] = None
    ):
        """Сохранение контекста разбора ситуаций"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "DELETE FROM analysis_context WHERE user_id = ?", (user_id,)
            )
            await conn.execute(
                """
                INSERT INTO analysis_context (user_id, context_data, goal, updated_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    user_id,
                    json.dumps(context_data, ensure_ascii=False),
                    goal,
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()

    async def get_analysis_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение контекста разбора ситуаций"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT context_data, goal FROM analysis_context WHERE user_id = ?",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return {
                        "context_data": json.loads(row[0]) if row[0] else {},
                        "goal": row[1],
                    }
        return None

    async def clear_analysis_context(self, user_id: int):
        """Очистка контекста разбора ситуаций"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "DELETE FROM analysis_context WHERE user_id = ?", (user_id,)
            )
            await conn.commit()

    async def save_toxic_context(
        self, user_id: int, context_data: Dict[str, Any], session_active: bool = True
    ):
        """Сохранение контекста токсичного собеседника"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                "DELETE FROM toxic_context WHERE user_id = ? AND session_active = 1",
                (user_id,),
            )
            await conn.execute(
                """
                INSERT INTO toxic_context (user_id, context_data, session_active, updated_at)
                VALUES (?, ?, ?, ?)
            """,
                (
                    user_id,
                    json.dumps(context_data, ensure_ascii=False),
                    1 if session_active else 0,
                    datetime.now().isoformat(),
                ),
            )
            await conn.commit()

    async def get_toxic_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение активного контекста токсичного собеседника"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT context_data FROM toxic_context WHERE user_id = ? AND session_active = 1",
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                if row:
                    return json.loads(row[0]) if row[0] else {}
        return None

    async def end_toxic_session(self, user_id: int):
        """Завершение сессии токсичного собеседника"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE toxic_context SET session_active = 0, updated_at = ?
                WHERE user_id = ? AND session_active = 1
            """,
                (datetime.now().isoformat(), user_id),
            )
            await conn.commit()

    async def save_message(
        self, user_id: int, module_type: str, message_text: str, response_text: str
    ):
        """Сохранение сообщения в историю"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO messages (user_id, module_type, message_text, response_text)
                VALUES (?, ?, ?, ?)
            """,
                (user_id, module_type, message_text, response_text),
            )
            await conn.commit()

    async def log_event(
        self, user_id: int, event_type: str, event_data: Dict[str, Any]
    ):
        """Логирование события (не критично, не пробрасываем ошибки)"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    INSERT INTO events (user_id, event_type, event_data)
                    VALUES (?, ?, ?)
                """,
                    (user_id, event_type, json.dumps(event_data, ensure_ascii=False)),
                )
                await conn.commit()
        except aiosqlite.Error as e:
            # Логирование событий не критично, просто логируем ошибку
            logger.warning(
                f"[Database] Failed to log event for user {user_id}, type {event_type}: {e}"
            )
        except Exception as e:
            logger.warning(
                f"[Database] Unexpected error logging event for user {user_id}: {e}"
            )

    async def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Получение последних событий"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT * FROM events ORDER BY created_at DESC LIMIT ?
            """,
                (limit,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "id": row["id"],
                        "user_id": row["user_id"],
                        "event_type": row["event_type"],
                        "event_data": (
                            json.loads(row["event_data"]) if row["event_data"] else {}
                        ),
                        "created_at": row["created_at"],
                    }
                    for row in rows
                ]

    # ==================== СИСТЕМА БАЛЛОВ ====================

    async def add_points(
        self,
        user_id: int,
        points: int,
        source: str,
        source_id: Optional[str] = None,
        description: Optional[str] = None,
    ) -> int:
        """Добавление баллов пользователю"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO user_points (user_id, points, source, source_id, description)
                VALUES (?, ?, ?, ?, ?)
            """,
                (user_id, points, source, source_id, description),
            )
            await conn.commit()

        # Проверяем достижение грейда
        total = await self.get_total_points(user_id)
        if total >= PointsConfig.GRADE_THRESHOLD:
            await self.set_user_grade(user_id, True)

        return total

    async def get_total_points(self, user_id: int) -> int:
        """Получение общего количества баллов пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                """
                SELECT COALESCE(SUM(points), 0) FROM user_points WHERE user_id = ?
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    async def get_points_breakdown(self, user_id: int) -> Dict[str, int]:
        """Получение разбивки баллов по источникам"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                """
                SELECT source, SUM(points) FROM user_points 
                WHERE user_id = ? GROUP BY source
            """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return {row[0]: row[1] for row in rows}

    async def set_user_grade(self, user_id: int, has_grade: bool):
        """Установка грейда пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                UPDATE users SET has_grade = ?, updated_at = ?
                WHERE user_id = ?
            """,
                (1 if has_grade else 0, datetime.now().isoformat(), user_id),
            )
            await conn.commit()

    async def has_user_grade(self, user_id: int) -> bool:
        """Проверка наличия грейда у пользователя"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT has_grade FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

    # ==================== ОНБОРДИНГ ====================

    async def is_onboarding_completed(self, user_id: int) -> bool:
        """Проверка завершения онбординга"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                "SELECT onboarding_completed FROM users WHERE user_id = ?", (user_id,)
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

    async def complete_onboarding(self, user_id: int) -> int:
        """Завершение онбординга и начисление баллов"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute(
                    """
                    UPDATE users SET onboarding_completed = 1, updated_at = ?
                    WHERE user_id = ?
                """,
                    (datetime.now().isoformat(), user_id),
                )
                await conn.commit()

            # Начисляем баллы за онбординг
            return await self.add_points(
                user_id,
                PointsConfig.ONBOARDING_COMPLETE,
                "onboarding",
                description="Прохождение онбординга",
            )
        except aiosqlite.Error as e:
            logger.error(
                f"[Database] Error completing onboarding for user {user_id}: {e}",
                exc_info=True,
            )
            raise
        except Exception as e:
            logger.exception(
                f"[Database] Unexpected error completing onboarding for user {user_id}: {e}"
            )
            raise

    # ==================== УРОКИ ====================

    async def get_lesson_progress(
        self, user_id: int, block_id: int, lesson_id: int
    ) -> bool:
        """Проверка прохождения урока"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                """
                SELECT completed FROM user_lesson_progress 
                WHERE user_id = ? AND block_id = ? AND lesson_id = ?
            """,
                (user_id, block_id, lesson_id),
            ) as cursor:
                row = await cursor.fetchone()
                return bool(row[0]) if row else False

    async def complete_lesson(
        self, user_id: int, block_id: int, lesson_id: int
    ) -> Optional[int]:
        """Завершение урока с начислением баллов"""
        # Проверяем, не был ли урок уже пройден
        if await self.get_lesson_progress(user_id, block_id, lesson_id):
            return None  # Урок уже пройден, баллы не начисляем

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT OR REPLACE INTO user_lesson_progress 
                (user_id, block_id, lesson_id, completed, completed_at)
                VALUES (?, ?, ?, 1, ?)
            """,
                (user_id, block_id, lesson_id, datetime.now().isoformat()),
            )
            await conn.commit()

        # Начисляем баллы за урок
        return await self.add_points(
            user_id,
            PointsConfig.LESSON_COMPLETE,
            "lesson",
            source_id=f"{block_id}_{lesson_id}",
            description=f"Урок {lesson_id} блока {block_id}",
        )

    async def get_all_lessons_progress(self, user_id: int) -> List[Dict[str, Any]]:
        """Получение прогресса по всем урокам"""
        async with aiosqlite.connect(self.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                """
                SELECT block_id, lesson_id, completed, completed_at 
                FROM user_lesson_progress WHERE user_id = ?
            """,
                (user_id,),
            ) as cursor:
                rows = await cursor.fetchall()
                return [
                    {
                        "block_id": row["block_id"],
                        "lesson_id": row["lesson_id"],
                        "completed": bool(row["completed"]),
                        "completed_at": row["completed_at"],
                    }
                    for row in rows
                ]

    async def get_completed_lessons_count(self, user_id: int) -> int:
        """Получение количества пройденных уроков"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                """
                SELECT COUNT(*) FROM user_lesson_progress 
                WHERE user_id = ? AND completed = 1
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 0

    # ==================== TOXIC CHAT РЕЗУЛЬТАТЫ ====================

    async def save_toxic_result(
        self,
        user_id: int,
        boundaries_score: int,
        manipulation_score: int,
        negotiation_score: int,
        feedback: str,
    ) -> int:
        """Сохранение результатов Toxic Chat сессии"""
        # Ограничиваем оценки от 1 до 10
        boundaries_score = max(1, min(10, boundaries_score))
        manipulation_score = max(1, min(10, manipulation_score))
        negotiation_score = max(1, min(10, negotiation_score))

        # Считаем общие баллы (макс 30)
        total_points = boundaries_score + manipulation_score + negotiation_score

        async with aiosqlite.connect(self.db_path) as conn:
            await conn.execute(
                """
                INSERT INTO toxic_results 
                (user_id, boundaries_score, manipulation_score, negotiation_score, total_points, feedback)
                VALUES (?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    boundaries_score,
                    manipulation_score,
                    negotiation_score,
                    total_points,
                    feedback,
                ),
            )
            await conn.commit()

        # Начисляем баллы
        await self.add_points(
            user_id,
            total_points,
            "toxic_chat",
            description=f"Toxic Chat: границы={boundaries_score}, манипуляции={manipulation_score}, переговоры={negotiation_score}",
        )

        return total_points

    async def get_toxic_stats(self, user_id: int) -> Dict[str, Any]:
        """Получение статистики по Toxic Chat"""
        async with aiosqlite.connect(self.db_path) as conn:
            async with conn.execute(
                """
                SELECT 
                    COUNT(*) as sessions,
                    COALESCE(SUM(total_points), 0) as total_points,
                    COALESCE(AVG(boundaries_score), 0) as avg_boundaries,
                    COALESCE(AVG(manipulation_score), 0) as avg_manipulation,
                    COALESCE(AVG(negotiation_score), 0) as avg_negotiation
                FROM toxic_results WHERE user_id = ?
            """,
                (user_id,),
            ) as cursor:
                row = await cursor.fetchone()
                return {
                    "sessions_count": row[0],
                    "total_points": row[1],
                    "avg_boundaries": round(row[2], 1),
                    "avg_manipulation": round(row[3], 1),
                    "avg_negotiation": round(row[4], 1),
                }


import sqlite3


# Обратная совместимость - синхронный класс для AtlantSDK и старых обработчиков
class Database:
    """
    Синхронная реализация для использования в AtlantSDK-обработчиках.
    Новая асинхронная логика должна использовать AsyncDatabase.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or Config.DATABASE_PATH

    # ===== Вспомогательные методы =====
    def get_connection(self):
        return sqlite3.connect(self.db_path)

    # ===== Аналитика (ANALYSIS) =====
    def get_analysis_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT context_data, goal FROM analysis_context WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "context_data": json.loads(row[0]) if row[0] else {},
                "goal": row[1],
            }
        return None

    def save_analysis_context(
        self, user_id: int, context_data: Dict[str, Any], goal: Optional[str] = None
    ):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_context WHERE user_id = ?", (user_id,))
        cursor.execute(
            """
            INSERT INTO analysis_context (user_id, context_data, goal, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                json.dumps(context_data, ensure_ascii=False),
                goal,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def clear_analysis_context(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM analysis_context WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()

    # ===== Toxic Chat (синхронная версия для AtlantSDK) =====
    def save_toxic_context(
        self, user_id: int, context_data: Dict[str, Any], session_active: bool = True
    ):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "DELETE FROM toxic_context WHERE user_id = ? AND session_active = 1",
            (user_id,),
        )
        cursor.execute(
            """
            INSERT INTO toxic_context (user_id, context_data, session_active, updated_at)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                json.dumps(context_data, ensure_ascii=False),
                1 if session_active else 0,
                datetime.now().isoformat(),
            ),
        )
        conn.commit()
        conn.close()

    def get_toxic_context(self, user_id: int) -> Optional[Dict[str, Any]]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT context_data FROM toxic_context WHERE user_id = ? AND session_active = 1",
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0]) if row[0] else {}
        return None

    def end_toxic_session(self, user_id: int):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE toxic_context SET session_active = 0, updated_at = ?
            WHERE user_id = ? AND session_active = 1
            """,
            (datetime.now().isoformat(), user_id),
        )
        conn.commit()
        conn.close()

    def save_toxic_result(
        self,
        user_id: int,
        boundaries_score: int,
        manipulation_score: int,
        negotiation_score: int,
        feedback: str,
    ) -> int:
        # Ограничиваем оценки от 1 до 10
        boundaries_score = max(1, min(10, boundaries_score))
        manipulation_score = max(1, min(10, manipulation_score))
        negotiation_score = max(1, min(10, negotiation_score))

        total_points = boundaries_score + manipulation_score + negotiation_score

        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO toxic_results 
            (user_id, boundaries_score, manipulation_score, negotiation_score, total_points, feedback)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                boundaries_score,
                manipulation_score,
                negotiation_score,
                total_points,
                feedback,
            ),
        )
        conn.commit()
        conn.close()

        # Также пишем в user_points, чтобы get_total_points работал корректно
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO user_points (user_id, points, source, description)
            VALUES (?, ?, ?, ?)
            """,
            (
                user_id,
                total_points,
                "toxic_chat",
                f"Toxic Chat: границы={boundaries_score}, манипуляции={manipulation_score}, переговоры={negotiation_score}",
            ),
        )
        conn.commit()
        conn.close()

        return total_points

    def get_total_points(self, user_id: int) -> int:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT COALESCE(SUM(points), 0) FROM user_points WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0

    # ===== Общие методы =====
    def save_message(
        self, user_id: int, module_type: str, message_text: str, response_text: str
    ):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (user_id, module_type, message_text, response_text)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, module_type, message_text, response_text),
        )
        conn.commit()
        conn.close()

    def log_event(self, user_id: int, event_type: str, event_data: Dict[str, Any]):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO events (user_id, event_type, event_data)
            VALUES (?, ?, ?)
            """,
            (user_id, event_type, json.dumps(event_data, ensure_ascii=False)),
        )
        conn.commit()
        conn.close()
