"""
Обработчики админ-панели
"""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

from core.config import Config
from core.container import Container
from bot.keyboards.admin import get_admin_main_keyboard

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь админом"""
    return user_id in Config.ADMIN_IDS


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Админ-панель"""
    user_id = message.from_user.id

    if not is_admin(user_id):
        await message.answer("❌ У тебя нет доступа к админ-панели")
        return

    text = """🔧 <b>Админ-панель</b>

Выбери раздел для управления:"""

    await message.answer(text, reply_markup=get_admin_main_keyboard())


@router.callback_query(F.data == "admin_main")
async def callback_admin_main(callback: CallbackQuery):
    """Главная админ-панель"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    text = """🔧 <b>Админ-панель</b>

Выбери раздел для управления:"""
    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_users")
async def callback_admin_users(callback: CallbackQuery):
    """Список пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    container = Container.get_instance()
    user_service = container.get_user_service()
    users = await user_service.get_all_users(limit=50)

    if not users:
        await callback.message.edit_text(
            "Пользователей пока нет", reply_markup=get_admin_main_keyboard()
        )
        await callback.answer()
        return

    text = f"👥 <b>Список пользователей</b> (показано: {len(users)})\n\n"

    for user in users[:20]:  # Показываем первые 20
        status = "✅" if user.is_active else "❌"
        username = user.username or "без username"
        text += f"{status} {user.user_id} - @{username} ({user.first_name or 'без имени'})\n"

    if len(users) > 20:
        text += f"\n... и ещё {len(users) - 20} пользователей"

    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard())
    await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def callback_admin_stats(callback: CallbackQuery):
    """Статистика"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У тебя нет доступа", show_alert=True)
        return

    container = Container.get_instance()
    lesson_service = container.get_lesson_service()
    user_service = container.get_user_service()

    # Получаем статистику
    total_users = len(await user_service.get_all_users())
    total_blocks = len(await lesson_service.get_all_blocks(include_inactive=True))
    total_lessons = await lesson_service.get_total_lessons_count()

    # Подсчитываем фрагменты
    blocks = await lesson_service.get_all_blocks(include_inactive=True)
    total_fragments = 0
    for block in blocks:
        lessons = await lesson_service.get_lessons_by_block(block.id)
        for lesson in lessons:
            fragments = await lesson_service.get_fragments_by_lesson(lesson.id)
            total_fragments += len(fragments)

    text = f"""📊 <b>Статистика</b>

👥 <b>Пользователей:</b> {total_users}
📚 <b>Блоков:</b> {total_blocks}
📖 <b>Уроков:</b> {total_lessons}
📄 <b>Фрагментов:</b> {total_fragments}"""

    await callback.message.edit_text(text, reply_markup=get_admin_main_keyboard())
    await callback.answer()
