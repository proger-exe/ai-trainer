"""
Обработчики онбординга (тестирования)
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.database import PointsConfig
from core.container import Container
from bot.keyboards import get_main_keyboard
from bot.keyboards.onboarding import (
    get_onboarding_start_keyboard,
    get_onboarding_step_keyboard,
    get_onboarding_question_keyboard,
)

router = Router()


class OnboardingStates(StatesGroup):
    """Состояния онбординга"""

    in_progress = State()


# Контент онбординга
ONBOARDING_STEPS = [
    {
        "type": "info",
        "title": "Добро пожаловать! 👋",
        "content": """Привет! Я — твой ИИ-тренажёр коммуникаций.

Я помогу тебе:
• Научиться устанавливать границы
• Распознавать манипуляции
• Эффективно вести переговоры
• Справляться с токсичными собеседниками

За прохождение знакомства ты получишь <b>+35 баллов</b>!

Давай познакомимся поближе? 🙂""",
    },
    {
        "type": "question",
        "title": "Вопрос 1 из 3 🎯",
        "content": """С какой ситуацией ты чаще всего сталкиваешься?

Это поможет мне понять, на чём сфокусироваться.""",
        "options": [
            "🛡️ Сложно отстаивать свои границы",
            "🎭 Чувствую, что мной манипулируют",
            "🤝 Не получается договариваться",
            "😤 Встречаю агрессию и токсичность",
        ],
    },
    {
        "type": "question",
        "title": "Вопрос 2 из 3 💭",
        "content": """Как ты обычно реагируешь на конфликт?""",
        "options": [
            "😶 Избегаю и молчу",
            "😠 Иду в атаку",
            "😔 Уступаю, чтобы не ссориться",
            "🗣️ Пытаюсь обсудить спокойно",
        ],
    },
    {
        "type": "question",
        "title": "Вопрос 3 из 3 ⏰",
        "content": """Сколько времени готов(а) уделять обучению?""",
        "options": [
            "⚡ 5 минут в день",
            "📖 15-20 минут в день",
            "📚 Когда будет время",
            "🎯 Хочу пройти всё сразу",
        ],
    },
    {
        "type": "info",
        "title": "Отлично! 🎉",
        "content": """Теперь я лучше понимаю твои потребности!

<b>Что тебя ждёт:</b>

📚 <b>Обучающий модуль</b> — 10 уроков в 3 блоках
• Границы
• Манипуляции и агрессия
• Переговоры

😤 <b>Toxic Chat</b> — практика с токсичным собеседником

📋 <b>Разбор ситуации</b> — анализ твоих реальных ситуаций

💬 <b>Нетворк-чат</b> — общение с единомышленниками

<b>Система баллов:</b>
• Урок = +50 баллов
• Toxic Chat = до 30 баллов
• При 1000 баллов — особый статус!

Готов(а) начать? 🚀""",
    },
]

TOTAL_ONBOARDING_STEPS = len(ONBOARDING_STEPS)


@router.callback_query(F.data == "onboarding_start")
async def callback_onboarding_start(callback: CallbackQuery, state: FSMContext):
    """Начало онбординга"""
    user_id = callback.from_user.id

    # Проверяем, не пройден ли уже онбординг
    container = Container.get_instance()
    db = container.get_db()
    if await db.is_onboarding_completed(user_id):
        await callback.answer("Онбординг уже пройден!", show_alert=True)
        return

    await state.set_state(OnboardingStates.in_progress)
    await state.update_data(step=1, answers={})

    # Показываем первый шаг
    step_data = ONBOARDING_STEPS[0]
    await show_onboarding_step(callback, step_data, 1)
    await callback.answer()


@router.callback_query(F.data == "onboarding_skip")
async def callback_onboarding_skip(callback: CallbackQuery, state: FSMContext):
    """Пропуск онбординга"""
    await state.clear()

    text = """🏠 <b>Главное меню</b>

Ты можешь пройти онбординг позже и получить +35 баллов.

Выбери, что тебя интересует:"""

    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("onboarding_step_"))
async def callback_onboarding_step(callback: CallbackQuery, state: FSMContext):
    """Переход к шагу онбординга"""
    step = int(callback.data.split("_")[-1])

    if step > TOTAL_ONBOARDING_STEPS:
        await callback.answer("Ошибка навигации", show_alert=True)
        return

    await state.update_data(step=step)
    step_data = ONBOARDING_STEPS[step - 1]
    await show_onboarding_step(callback, step_data, step)
    await callback.answer()


@router.callback_query(F.data.startswith("onboarding_answer_"))
async def callback_onboarding_answer(callback: CallbackQuery, state: FSMContext):
    """Ответ на вопрос онбординга"""
    parts = callback.data.split("_")
    step = int(parts[2])
    answer_idx = int(parts[3])

    # Сохраняем ответ
    data = await state.get_data()
    answers = data.get("answers", {})
    answers[step] = answer_idx
    await state.update_data(answers=answers)

    # Переходим к следующему шагу
    next_step = step + 1
    if next_step > TOTAL_ONBOARDING_STEPS:
        # Это был последний вопрос, показываем финальный экран
        await state.update_data(step=TOTAL_ONBOARDING_STEPS)
        step_data = ONBOARDING_STEPS[TOTAL_ONBOARDING_STEPS - 1]
        await show_onboarding_step(callback, step_data, TOTAL_ONBOARDING_STEPS)
    else:
        await state.update_data(step=next_step)
        step_data = ONBOARDING_STEPS[next_step - 1]
        await show_onboarding_step(callback, step_data, next_step)

    await callback.answer()


@router.callback_query(F.data == "onboarding_complete")
async def callback_onboarding_complete(callback: CallbackQuery, state: FSMContext):
    """Завершение онбординга"""
    user_id = callback.from_user.id

    # Проверяем, не пройден ли уже
    container = Container.get_instance()
    db = container.get_db()
    if await db.is_onboarding_completed(user_id):
        await callback.answer("Онбординг уже пройден!", show_alert=True)
        await state.clear()
        return

    # Завершаем онбординг и начисляем баллы
    total_points = await db.complete_onboarding(user_id)

    # Логируем событие
    data = await state.get_data()
    await db.log_event(
        user_id,
        "onboarding_completed",
        {
            "answers": data.get("answers", {}),
            "points_earned": PointsConfig.ONBOARDING_COMPLETE,
        },
    )

    await state.clear()

    text = f"""🎉 <b>Поздравляем!</b>

Ты успешно прошёл(ла) знакомство с ботом!

<b>+{PointsConfig.ONBOARDING_COMPLETE} баллов</b> начислено!
💎 Всего баллов: <b>{total_points}</b>

Теперь ты готов(а) начать обучение. Рекомендую начать с первого блока — <b>Границы</b>.

Удачи! 🚀"""

    await callback.message.edit_text(text, reply_markup=get_main_keyboard())
    await callback.answer(f"+{PointsConfig.ONBOARDING_COMPLETE} баллов!")


async def show_onboarding_step(callback: CallbackQuery, step_data: dict, step_num: int):
    """Показать шаг онбординга"""
    title = step_data["title"]
    content = step_data["content"]
    step_type = step_data["type"]

    text = f"<b>{title}</b>\n\n{content}"

    if step_type == "question":
        keyboard = get_onboarding_question_keyboard(step_num, step_data["options"])
    else:
        keyboard = get_onboarding_step_keyboard(step_num, TOTAL_ONBOARDING_STEPS)

    await callback.message.edit_text(text, reply_markup=keyboard)
