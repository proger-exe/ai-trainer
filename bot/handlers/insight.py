"""
Обработчики для Daily Insight
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
import json
from datetime import date, datetime, timedelta
from typing import Optional
import random

from core.database import PointsConfig
from core.container import Container
from bot.keyboards.insight import (
    get_insight_keyboard,
    get_insight_claimed_keyboard,
    get_insight_already_viewed_keyboard,
    get_insight_settings_keyboard,
    get_insight_time_keyboard,
    get_insight_category_keyboard,
)
from bot.keyboards import get_main_keyboard
from bot.models.insight import (
    Insight,
    InsightCategory,
    InsightConfig,
    InsightStats,
    DEFAULT_INSIGHTS,
)

router = Router()


async def init_default_insights():
    """Инициализация базовых инсайтов в БД"""
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        # Проверяем, есть ли уже инсайты
        async with conn.execute("SELECT COUNT(*) FROM insights") as cursor:
            row = await cursor.fetchone()
            if row[0] > 0:
                return  # Инсайты уже есть

        # Добавляем базовые инсайты
        for insight in DEFAULT_INSIGHTS:
            await conn.execute(
                """
                INSERT INTO insights (category, title, content, tip, emoji, is_ai_generated)
                VALUES (?, ?, ?, ?, ?, 0)
            """,
                (
                    insight.category.value,
                    insight.title,
                    insight.content,
                    insight.tip,
                    insight.emoji,
                ),
            )

        await conn.commit()


async def get_todays_insight(user_id: int) -> tuple[Optional[Insight], bool]:
    """Получить инсайт дня для пользователя. Возвращает (insight, already_viewed)"""
    container = Container.get_instance()
    db = container.get_db()
    today = date.today().isoformat()

    async with db.get_connection() as conn:
        # Проверяем, просматривал ли уже сегодня
        async with conn.execute(
            """
            SELECT insight_id, points_earned FROM user_insights 
            WHERE user_id = ? AND insight_date = ?
        """,
            (user_id, today),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Уже просматривал - возвращаем тот же инсайт
                insight_id = row[0]
                already_earned = row[1] > 0

                async with conn.execute(
                    "SELECT * FROM insights WHERE id = ?", (insight_id,)
                ) as cursor2:
                    insight_row = await cursor2.fetchone()
                    if insight_row:
                        return (
                            Insight(
                                id=insight_row[0],
                                category=InsightCategory(insight_row[1]),
                                title=insight_row[2],
                                content=insight_row[3],
                                tip=insight_row[4],
                                emoji=insight_row[5],
                                is_ai_generated=bool(insight_row[6]),
                            ),
                            already_earned,
                        )

        # Получаем случайный инсайт, который пользователь ещё не видел недавно
        async with conn.execute(
            """
            SELECT i.* FROM insights i
            WHERE i.id NOT IN (
                SELECT insight_id FROM user_insights 
                WHERE user_id = ? AND insight_date > date('now', '-7 days')
            )
            ORDER BY RANDOM()
            LIMIT 1
        """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

            if not row:
                # Если все просмотрены - берём любой случайный
                async with conn.execute(
                    "SELECT * FROM insights ORDER BY RANDOM() LIMIT 1"
                ) as cursor2:
                    row = await cursor2.fetchone()

            if row:
                insight = Insight(
                    id=row[0],
                    category=InsightCategory(row[1]),
                    title=row[2],
                    content=row[3],
                    tip=row[4],
                    emoji=row[5],
                    is_ai_generated=bool(row[6]),
                )

                # Сохраняем как просмотренный (но ещё без баллов)
                await conn.execute(
                    """
                    INSERT INTO user_insights (user_id, insight_id, insight_date, points_earned)
                    VALUES (?, ?, ?, 0)
                """,
                    (user_id, insight.id, today),
                )
                await conn.commit()

                return insight, False

    return None, False


async def claim_insight_points(user_id: int, insight_id: int) -> int:
    """Начислить баллы за инсайт. Возвращает количество баллов или 0 если уже получены"""
    container = Container.get_instance()
    db = container.get_db()
    today = date.today().isoformat()

    async with db.get_connection() as conn:
        # Проверяем, не получены ли уже баллы
        async with conn.execute(
            """
            SELECT points_earned FROM user_insights 
            WHERE user_id = ? AND insight_date = ? AND insight_id = ?
        """,
            (user_id, today, insight_id),
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0] > 0:
                return 0  # Баллы уже получены

        # Начисляем баллы
        points = InsightConfig.POINTS_PER_INSIGHT

        # Проверяем серию
        streak = await get_insight_streak(user_id)
        if streak > 0 and streak % 7 == 0:
            points += InsightConfig.STREAK_BONUS

        # Обновляем запись
        await conn.execute(
            """
            UPDATE user_insights SET points_earned = ?, viewed_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND insight_date = ?
        """,
            (points, user_id, today),
        )
        await conn.commit()

    # Добавляем в общий счёт баллов
    await db.add_points(
        user_id,
        points,
        "insight",
        source_id=str(insight_id),
        description=f"Daily Insight {today}",
    )

    return points


async def get_insight_streak(user_id: int) -> int:
    """Получить текущую серию дней просмотра инсайтов"""
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        async with conn.execute(
            """
            SELECT insight_date FROM user_insights 
            WHERE user_id = ? AND points_earned > 0
            ORDER BY insight_date DESC
        """,
            (user_id,),
        ) as cursor:
            rows = await cursor.fetchall()

            if not rows:
                return 0

            streak = 0
            expected_date = date.today()

            for row in rows:
                insight_date = date.fromisoformat(row[0])
                if insight_date == expected_date:
                    streak += 1
                    expected_date -= timedelta(days=1)
                elif insight_date < expected_date:
                    break

            return streak


async def get_insight_stats(user_id: int) -> InsightStats:
    """Получить статистику инсайтов пользователя"""
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        # Общее количество и баллы
        async with conn.execute(
            """
            SELECT COUNT(*), COALESCE(SUM(points_earned), 0) 
            FROM user_insights WHERE user_id = ? AND points_earned > 0
        """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            total_viewed = row[0]
            total_points = row[1]

        # Серия
        streak = await get_insight_streak(user_id)

        # Лучшая серия
        # (упрощённо - берём текущую серию как лучшую для MVP)
        best_streak = streak

        # Последняя дата
        async with conn.execute(
            """
            SELECT MAX(insight_date) FROM user_insights 
            WHERE user_id = ? AND points_earned > 0
        """,
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            last_date = date.fromisoformat(row[0]) if row[0] else None

        return InsightStats(
            total_viewed=total_viewed,
            total_points=total_points,
            streak_days=streak,
            best_streak=best_streak,
            last_viewed_date=last_date,
        )


@router.callback_query(F.data == "daily_insight")
async def callback_daily_insight(callback: CallbackQuery):
    """Показать инсайт дня"""
    user_id = callback.from_user.id

    # Убедимся, что базовые инсайты существуют
    await init_default_insights()

    insight, already_earned = await get_todays_insight(user_id)

    if not insight:
        await callback.answer("Инсайты временно недоступны", show_alert=True)
        return

    # Формируем текст
    text = f"""💡 <b>Daily Insight</b>

{insight.emoji} <b>{insight.title}</b>

{insight.content}

<b>💪 Практика:</b>
<i>{insight.tip}</i>"""

    if already_earned:
        text += "\n\n✅ <i>Баллы за сегодня уже получены</i>"
        keyboard = get_insight_already_viewed_keyboard()
    else:
        text += f"\n\n🎁 <b>+{InsightConfig.POINTS_PER_INSIGHT} баллов</b> за просмотр!"
        keyboard = get_insight_keyboard(insight.id, has_points=True)

    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data.startswith("insight_claim_"))
async def callback_insight_claim(callback: CallbackQuery):
    """Получить баллы за инсайт"""
    user_id = callback.from_user.id
    insight_id = int(callback.data.replace("insight_claim_", ""))

    points = await claim_insight_points(user_id, insight_id)

    if points == 0:
        await callback.answer("Баллы уже получены!", show_alert=True)
        return

    # Получаем статистику
    stats = await get_insight_stats(user_id)

    streak_text = ""
    if stats.streak_days > 1:
        streak_text = f"\n🔥 Серия: <b>{stats.streak_days} дней подряд!</b>"

    bonus_text = ""
    if points > InsightConfig.POINTS_PER_INSIGHT:
        bonus_text = f"\n🎁 Бонус за серию: +{InsightConfig.STREAK_BONUS}"

    container = Container.get_instance()
    points_service = container.get_points_service()
    total_points = await points_service.get_total_points(user_id)

    text = f"""✅ <b>Инсайт получен!</b>

<b>+{points} баллов</b>{bonus_text}{streak_text}

💎 Всего баллов: <b>{total_points}</b>

Приходи завтра за новым инсайтом! 📆"""

    await callback.message.edit_text(text, reply_markup=get_insight_claimed_keyboard())
    await callback.answer(f"+{points} баллов!")


@router.callback_query(F.data == "insight_stats")
async def callback_insight_stats(callback: CallbackQuery):
    """Статистика инсайтов"""
    user_id = callback.from_user.id
    stats = await get_insight_stats(user_id)

    text = f"""📊 <b>Статистика Daily Insight</b>

📚 Просмотрено: <b>{stats.total_viewed}</b> инсайтов
💎 Заработано: <b>{stats.total_points}</b> баллов
🔥 Текущая серия: <b>{stats.streak_days}</b> дней
🏆 Лучшая серия: <b>{stats.best_streak}</b> дней

<b>Как это работает:</b>
• Каждый день — новый инсайт
• +{InsightConfig.POINTS_PER_INSIGHT} баллов за просмотр
• +{InsightConfig.STREAK_BONUS} бонус каждые 7 дней подряд"""

    from aiogram.utils.keyboard import InlineKeyboardBuilder

    builder = InlineKeyboardBuilder()
    builder.button(text="💡 Сегодняшний инсайт", callback_data="daily_insight")
    builder.button(text="⚙️ Настройки", callback_data="insight_settings")
    builder.button(text="🏠 Домой", callback_data="home")
    builder.adjust(1)

    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "insight_settings")
async def callback_insight_settings(callback: CallbackQuery):
    """Настройки уведомлений об инсайтах"""
    user_id = callback.from_user.id

    # Получаем текущие настройки
    container = Container.get_instance()
    db = container.get_db()

    is_enabled = True  # По умолчанию включено

    async with db.get_connection() as conn:
        async with conn.execute(
            "SELECT daily_insight_enabled FROM user_settings WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                is_enabled = bool(row[0])

    text = """⚙️ <b>Настройки Daily Insight</b>

Ежедневные инсайты помогают:
• Получать полезные советы каждый день
• Зарабатывать баллы
• Формировать полезную привычку"""

    await callback.message.edit_text(
        text, reply_markup=get_insight_settings_keyboard(is_enabled)
    )
    await callback.answer()


@router.callback_query(F.data == "insight_toggle")
async def callback_insight_toggle(callback: CallbackQuery):
    """Переключить уведомления об инсайтах"""
    user_id = callback.from_user.id
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        # Получаем текущее состояние
        async with conn.execute(
            "SELECT daily_insight_enabled FROM user_settings WHERE user_id = ?",
            (user_id,),
        ) as cursor:
            row = await cursor.fetchone()

            if row:
                new_state = 0 if row[0] else 1
                await conn.execute(
                    """
                    UPDATE user_settings SET daily_insight_enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """,
                    (new_state, user_id),
                )
            else:
                new_state = 0  # По умолчанию было включено, значит выключаем
                await conn.execute(
                    """
                    INSERT INTO user_settings (user_id, daily_insight_enabled)
                    VALUES (?, ?)
                """,
                    (user_id, new_state),
                )

            await conn.commit()

    status = "включены" if new_state else "отключены"
    await callback.answer(f"Уведомления {status}", show_alert=True)

    # Обновляем меню
    await callback_insight_settings(callback)


@router.callback_query(F.data == "insight_change_time")
async def callback_insight_change_time(callback: CallbackQuery):
    """Изменить время уведомления"""
    text = """⏰ <b>Выбери время уведомления</b>

В это время тебе будет приходить напоминание о новом инсайте дня."""

    await callback.message.edit_text(text, reply_markup=get_insight_time_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("insight_time_"))
async def callback_insight_set_time(callback: CallbackQuery):
    """Установить время уведомления"""
    user_id = callback.from_user.id
    time_str = callback.data.replace("insight_time_", "")
    formatted_time = f"{time_str[:2]}:{time_str[2:]}"

    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        await conn.execute(
            """
            INSERT INTO user_settings (user_id, insight_time)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET insight_time = ?, updated_at = CURRENT_TIMESTAMP
        """,
            (user_id, formatted_time, formatted_time),
        )
        await conn.commit()

    await callback.answer(f"Время установлено: {formatted_time}", show_alert=True)
    await callback_insight_settings(callback)
