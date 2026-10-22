"""
Расширенный онбординг с погружением во все функции
"""

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from core.database import PointsConfig
from core.container import Container
from core.bridge import bridge
from bot.keyboards import get_main_keyboard
from bot.keyboards.onboarding_extended import (
    get_onboarding_welcome_keyboard,
    get_onboarding_question_keyboard,
    get_onboarding_phase_keyboard,
    get_onboarding_demo_learning_keyboard,
    get_onboarding_demo_analysis_keyboard,
    get_onboarding_recommendation_keyboard,
    get_onboarding_goal_keyboard,
    get_onboarding_complete_keyboard,
    get_onboarding_progress_indicator,
)
from bot.keyboards.toxic_extended import get_toxic_session_keyboard
from bot.models.onboarding import OnboardingPhase, OnboardingConfig

router = Router()


class OnboardingExtendedStates(StatesGroup):
    """Состояния расширенного онбординга"""

    in_progress = State()
    demo_toxic = State()  # Демо токсик-чата
    awaiting_recommendation = State()  # Ожидание AI-рекомендации


# Расширенный контент онбординга
ONBOARDING_CONTENT = {
    OnboardingPhase.WELCOME: {
        "title": "Добро пожаловать! 👋",
        "content": """Привет! Я — твой ИИ-тренажёр коммуникаций.

Я помогу тебе:
• 🛡️ Устанавливать и защищать границы
• 🎭 Распознавать манипуляции
• 🤝 Эффективно вести переговоры
• 😤 Справляться с токсичными собеседниками

За прохождение знакомства ты получишь <b>+{points} баллов</b>!

Давай познакомимся поближе? 🙂""".format(
            points=OnboardingConfig.TOTAL_POINTS
        ),
    },
}

# Вопросы онбординга теперь хранятся в БД и загружаются через OnboardingService


# Демо-урок
DEMO_LESSON = {
    "title": "📚 Демо-урок: Что такое границы?",
    "content": """<b>Личные границы</b> — это невидимые линии, которые определяют:
• Что для вас приемлемо, а что нет
• Как с вами можно обращаться
• Где заканчиваетесь вы и начинаются другие

<b>Пример:</b>
❌ «Можешь поработать в выходные? Ну пожааалуйста!»
✅ «Я ценю доверие, но выходные — моё личное время. Давай обсудим, как справиться в рабочие дни.»

<i>Это был краткий демо-урок. В полной версии тебя ждут практические упражнения и разборы ситуаций!</i>""",
}

# Демо-анализ
DEMO_ANALYSIS = {
    "title": "📋 Демо: Разбор ситуации",
    "content": """<b>Как работает разбор:</b>

1️⃣ Ты описываешь свою ситуацию или загружаешь скриншот переписки

2️⃣ Я анализирую контекст и даю:
• 💬 Лучший вариант ответа
• 🎯 Прогноз реакции собеседника
• 📝 Следующие шаги
• 🔄 Альтернативные стратегии

<b>Пример ситуации:</b>
<i>«Коллега постоянно перекидывает на меня свою работу, ссылаясь на занятость...»</i>

<b>Мой анализ включит:</b>
• Что на самом деле происходит
• Почему это работает
• Как ответить без конфликта
• Как предотвратить в будущем

<i>Готов(а) попробовать с реальной ситуацией?</i>""",
}


async def get_user_onboarding_progress(user_id: int) -> dict:
    """Получить прогресс онбординга пользователя"""
    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        async with conn.execute(
            "SELECT * FROM onboarding_progress WHERE user_id = ?", (user_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
    return None


async def save_onboarding_progress(user_id: int, data: dict):
    """Сохранить прогресс онбординга"""
    import json

    container = Container.get_instance()
    db = container.get_db()

    async with db.get_connection() as conn:
        await conn.execute(
            """
            INSERT OR REPLACE INTO onboarding_progress 
            (user_id, current_phase, current_step, answers, 
             demo_learning_done, demo_toxic_done, demo_tasks_done,
             recommended_block, ai_recommendation, started_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """,
            (
                user_id,
                data.get("current_phase", "welcome"),
                data.get("current_step", 0),
                json.dumps(data.get("answers", {}), ensure_ascii=False),
                1 if data.get("demo_learning_done") else 0,
                1 if data.get("demo_toxic_done") else 0,
                1 if data.get("demo_tasks_done") else 0,
                data.get("recommended_block"),
                data.get("ai_recommendation"),
            ),
        )
        await conn.commit()


@router.callback_query(F.data == "onboarding_extended_start")
async def callback_onboarding_start(callback: CallbackQuery, state: FSMContext):
    """Начало расширенного онбординга"""
    user_id = callback.from_user.id

    # Проверяем, не пройден ли уже онбординг
    container = Container.get_instance()
    db = container.get_db()
    if await db.is_onboarding_completed(user_id):
        await callback.answer("Онбординг уже пройден!", show_alert=True)
        return

    await state.set_state(OnboardingExtendedStates.in_progress)
    await state.update_data(phase=OnboardingPhase.QUESTIONS.value, step=0, answers={})

    # Сохраняем начало в БД
    await save_onboarding_progress(
        user_id,
        {
            "current_phase": OnboardingPhase.QUESTIONS.value,
            "current_step": 0,
            "answers": {},
        },
    )

    # Получаем вопросы из БД
    container = Container.get_instance()
    onboarding_service = container.get_onboarding_service()
    questions = await onboarding_service.get_active_questions_ordered()

    if not questions:
        await callback.answer(
            "❌ Вопросы онбординга не настроены. Обратитесь к администратору.",
            show_alert=True,
        )
        return

    # Показываем первый вопрос
    question = questions[0]
    progress = get_onboarding_progress_indicator(OnboardingPhase.QUESTIONS)

    text = f"""{progress}

<b>{question.title}</b>

{question.content}"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_question_keyboard(0, question.options)
    )
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

    # Получаем вопросы из БД
    container = Container.get_instance()
    onboarding_service = container.get_onboarding_service()
    questions = await onboarding_service.get_active_questions_ordered()

    if step >= len(questions):
        await callback.answer("❌ Ошибка: вопрос не найден", show_alert=True)
        return

    question_key = questions[step].question_key
    answers[question_key] = answer_idx
    await state.update_data(answers=answers)

    # Переходим к следующему вопросу или фазе
    next_step = step + 1

    if next_step < len(questions):
        # Следующий вопрос
        question = questions[next_step]
        progress = get_onboarding_progress_indicator(OnboardingPhase.QUESTIONS)

        text = f"""{progress}

<b>{question.title}</b>

{question.content}"""

        await callback.message.edit_text(
            text,
            reply_markup=get_onboarding_question_keyboard(next_step, question.options),
        )
    else:
        # Вопросы закончились - переходим к демо обучения
        await state.update_data(phase=OnboardingPhase.DEMO_LEARNING.value)

        # Начисляем баллы за вопросы
        container = Container.get_instance()
        db = container.get_db()
        await db.add_points(
            callback.from_user.id,
            PointsConfig.ONBOARDING_QUESTIONS,
            "onboarding",
            source_id="questions",
            description="Прохождение вопросов онбординга",
        )

        progress = get_onboarding_progress_indicator(OnboardingPhase.DEMO_LEARNING)

        text = f"""{progress}

<b>Отлично! 🎉</b>

Теперь давай познакомлю тебя с возможностями бота.

<b>📚 Обучающий модуль</b>
10 уроков в 3 блоках:
• Границы
• Манипуляции и агрессия
• Переговоры

Хочешь попробовать мини-урок?"""

        await callback.message.edit_text(
            text,
            reply_markup=get_onboarding_phase_keyboard(OnboardingPhase.DEMO_LEARNING),
        )

    await callback.answer()


@router.callback_query(F.data == "onboarding_demo_learning")
async def callback_demo_learning(callback: CallbackQuery, state: FSMContext):
    """Демо урока"""
    progress = get_onboarding_progress_indicator(OnboardingPhase.DEMO_LEARNING)

    text = f"""{progress}

{DEMO_LESSON["title"]}

{DEMO_LESSON["content"]}"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_demo_learning_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.in_({"onboarding_demo_learning_done", "onboarding_skip_demo_learning"})
)
async def callback_demo_learning_done(callback: CallbackQuery, state: FSMContext):
    """Демо урока завершено"""
    user_id = callback.from_user.id
    is_done = callback.data == "onboarding_demo_learning_done"

    await state.update_data(
        phase=OnboardingPhase.DEMO_TOXIC.value, demo_learning_done=is_done
    )

    # Начисляем баллы если прошёл демо
    if is_done:
        container = Container.get_instance()
        db = container.get_db()
        await db.add_points(
            user_id,
            PointsConfig.ONBOARDING_DEMO_LEARNING,
            "onboarding",
            source_id="demo_learning",
            description="Демо обучающего модуля",
        )

    progress = get_onboarding_progress_indicator(OnboardingPhase.DEMO_TOXIC)

    text = f"""{progress}

<b>😤 Toxic Chat</b>

Это уникальный тренажёр, где ты практикуешь общение с токсичным собеседником в безопасной среде.

<b>Что это даёт:</b>
• Тренировка реакции на провокации
• Практика установления границ
• Обратная связь от ИИ по твоему поведению
• Заработок до 30 баллов за сессию

Хочешь попробовать короткую демо-сессию?"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_phase_keyboard(OnboardingPhase.DEMO_TOXIC)
    )
    await callback.answer()


@router.callback_query(F.data == "onboarding_demo_toxic")
async def callback_demo_toxic_start(callback: CallbackQuery, state: FSMContext):
    """Запуск демо Toxic Chat"""
    user_id = callback.from_user.id

    await state.set_state(OnboardingExtendedStates.demo_toxic)

    text = """<b>🎮 Демо Toxic Chat</b>

Сейчас ты пообщаешься с токсичным собеседником. 

<b>Твоя задача:</b> Сохранить спокойствие и установить границы.

<i>Это короткая демо-версия. Напиши 2-3 сообщения, чтобы понять как это работает.</i>

Токсичный собеседник начинает диалог..."""

    await callback.message.edit_text(
        text, reply_markup=get_toxic_session_keyboard(is_demo=True)
    )

    # Запускаем демо-сессию через bridge
    command = f"START_TOXIC_DEMO {user_id} => TOXIC"
    bridge.send_to_atlant(command)

    await callback.answer()


@router.callback_query(F.data == "onboarding_demo_toxic_done")
async def callback_demo_toxic_done(callback: CallbackQuery, state: FSMContext):
    """Демо Toxic Chat завершено"""
    user_id = callback.from_user.id

    await state.set_state(OnboardingExtendedStates.in_progress)
    await state.update_data(
        phase=OnboardingPhase.DEMO_TASKS.value, demo_toxic_done=True
    )

    # Начисляем баллы
    container = Container.get_instance()
    db = container.get_db()
    await db.add_points(
        user_id,
        PointsConfig.ONBOARDING_DEMO_TOXIC,
        "onboarding",
        source_id="demo_toxic",
        description="Демо Toxic Chat",
    )

    # Завершаем демо-сессию
    await db.end_toxic_session(user_id)

    progress = get_onboarding_progress_indicator(OnboardingPhase.DEMO_TASKS)

    text = f"""{progress}

<b>📋 Разбор ситуации</b>

Здесь ты можешь описать реальную ситуацию из жизни, и я помогу:
• Разобрать, что происходит
• Найти лучший ответ
• Спрогнозировать реакцию собеседника
• Дать альтернативные стратегии

Хочешь увидеть пример?"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_phase_keyboard(OnboardingPhase.DEMO_TASKS)
    )
    await callback.answer()


@router.callback_query(F.data.in_({"onboarding_skip_demo_toxic"}))
async def callback_skip_demo_toxic(callback: CallbackQuery, state: FSMContext):
    """Пропуск демо Toxic Chat"""
    await state.update_data(
        phase=OnboardingPhase.DEMO_TASKS.value, demo_toxic_done=False
    )

    progress = get_onboarding_progress_indicator(OnboardingPhase.DEMO_TASKS)

    text = f"""{progress}

<b>📋 Разбор ситуации</b>

Здесь ты можешь описать реальную ситуацию из жизни, и я помогу:
• Разобрать, что происходит
• Найти лучший ответ
• Спрогнозировать реакцию собеседника
• Дать альтернативные стратегии

Хочешь увидеть пример?"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_phase_keyboard(OnboardingPhase.DEMO_TASKS)
    )
    await callback.answer()


@router.callback_query(F.data == "onboarding_demo_analysis")
async def callback_demo_analysis(callback: CallbackQuery, state: FSMContext):
    """Демо разбора ситуации"""
    progress = get_onboarding_progress_indicator(OnboardingPhase.DEMO_TASKS)

    text = f"""{progress}

{DEMO_ANALYSIS["title"]}

{DEMO_ANALYSIS["content"]}"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_demo_analysis_keyboard()
    )
    await callback.answer()


@router.callback_query(
    F.data.in_({"onboarding_demo_analysis_done", "onboarding_skip_demo_analysis"})
)
async def callback_demo_analysis_done(callback: CallbackQuery, state: FSMContext):
    """Демо анализа завершено - переход к рекомендации"""
    user_id = callback.from_user.id
    is_done = callback.data == "onboarding_demo_analysis_done"

    await state.set_state(OnboardingExtendedStates.awaiting_recommendation)
    await state.update_data(
        phase=OnboardingPhase.RECOMMENDATION.value, demo_tasks_done=is_done
    )

    # Начисляем баллы если прошёл демо
    if is_done:
        container = Container.get_instance()
        db = container.get_db()
        await db.add_points(
            user_id,
            PointsConfig.ONBOARDING_DEMO_TASKS,
            "onboarding",
            source_id="demo_tasks",
            description="Демо разбора ситуаций",
        )

    progress = get_onboarding_progress_indicator(OnboardingPhase.RECOMMENDATION)

    text = f"""{progress}

<b>🎯 Персональная рекомендация</b>

На основе твоих ответов я проанализирую, с какого блока тебе лучше начать обучение.

Это поможет получить максимум пользы с первых шагов!"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_phase_keyboard(OnboardingPhase.RECOMMENDATION)
    )
    await callback.answer()


@router.callback_query(F.data == "onboarding_get_recommendation")
async def callback_get_recommendation(callback: CallbackQuery, state: FSMContext):
    """Получение AI-рекомендации"""
    user_id = callback.from_user.id
    data = await state.get_data()
    answers = data.get("answers", {})

    # Показываем загрузку
    await callback.message.edit_text("⏳ Анализирую твои ответы...")

    # Получаем вопросы из БД для формирования полных данных
    container = Container.get_instance()
    onboarding_service = container.get_onboarding_service()
    questions = await onboarding_service.get_active_questions_ordered()

    # Формируем полные данные с текстами ответов
    import json

    full_answers = {}
    for question in questions:
        question_key = question.question_key
        answer_idx = answers.get(question_key)
        if answer_idx is not None and 0 <= answer_idx < len(question.options):
            full_answers[question_key] = {
                "index": answer_idx,
                "text": question.options[answer_idx],
                "question": question.content,
            }

    # Отправляем запрос на получение рекомендации
    answers_json = json.dumps(full_answers, ensure_ascii=False)
    command = f"ONBOARDING_RECOMMEND {user_id}&&{answers_json} => ANALYSIS"
    bridge.send_to_atlant(command)

    await callback.answer()


@router.callback_query(F.data.startswith("onboarding_start_block_"))
async def callback_start_recommended_block(callback: CallbackQuery, state: FSMContext):
    """Начать с рекомендованного блока"""
    block_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id

    # Переходим к установке цели
    await state.update_data(
        phase=OnboardingPhase.GOAL_SETTING.value, recommended_block=block_id
    )

    progress = get_onboarding_progress_indicator(OnboardingPhase.GOAL_SETTING)

    text = f"""{progress}

<b>🏆 Твоя первая цель</b>

Чтобы закрепить мотивацию, предлагаю тебе цель:

<b>Набрать первые 1000 баллов!</b>

<b>Что это даст:</b>
• 🏆 Особый статус в сообществе
• 🎁 Доступ к секретному модулю
• 👥 Приглашение в закрытую группу (ежемесячные созвоны)
• 📊 Место в топе лидерборда

<b>Как заработать:</b>
• Уроки — +50 баллов
• Toxic Chat — до +30 баллов
• Daily Insight — +15 баллов
• Онбординг — +50 баллов"""

    await callback.message.edit_text(text, reply_markup=get_onboarding_goal_keyboard())
    await callback.answer()


@router.callback_query(F.data == "onboarding_view_all_blocks")
async def callback_view_all_blocks(callback: CallbackQuery, state: FSMContext):
    """Показать все блоки"""
    # Переход к выбору блока после онбординга
    await callback.message.edit_text(
        "После завершения онбординга ты сможешь выбрать любой блок для изучения.",
        reply_markup=get_onboarding_goal_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "onboarding_to_goal")
async def callback_to_goal(callback: CallbackQuery, state: FSMContext):
    """Переход к установке цели"""
    await state.update_data(phase=OnboardingPhase.GOAL_SETTING.value)

    progress = get_onboarding_progress_indicator(OnboardingPhase.GOAL_SETTING)

    text = f"""{progress}

<b>🏆 Твоя первая цель</b>

Чтобы закрепить мотивацию, предлагаю тебе цель:

<b>Набрать первые 1000 баллов!</b>

<b>Что это даст:</b>
• 🏆 Особый статус в сообществе
• 🎁 Доступ к секретному модулю
• 👥 Приглашение в закрытую группу (ежемесячные созвоны)
• 📊 Место в топе лидерборда"""

    await callback.message.edit_text(text, reply_markup=get_onboarding_goal_keyboard())
    await callback.answer()


@router.callback_query(F.data == "onboarding_goal_info")
async def callback_goal_info(callback: CallbackQuery):
    """Информация о награде за цель"""
    text = """<b>🎁 Что ты получишь за 1000 баллов:</b>

<b>🏆 Особый статус</b>
Бейдж в профиле и признание в сообществе

<b>📚 Секретный модуль</b>
Продвинутые техники переговоров

<b>👥 Закрытая группа</b>
• Общение с единомышленниками
• Ежемесячные Zoom-созвоны
• Разборы сложных кейсов

<b>📊 Лидерборд</b>
Твоё имя в топе самых активных участников"""

    await callback.answer(text, show_alert=True)


@router.callback_query(F.data == "onboarding_accept_goal")
async def callback_accept_goal(callback: CallbackQuery, state: FSMContext):
    """Принятие цели и завершение онбординга"""
    user_id = callback.from_user.id
    data = await state.get_data()

    # Завершаем онбординг
    container = Container.get_instance()
    db = container.get_db()

    # Финальные баллы
    await db.add_points(
        user_id,
        PointsConfig.ONBOARDING_FINAL,
        "onboarding",
        source_id="complete",
        description="Завершение онбординга",
    )

    # Отмечаем онбординг как завершённый
    total_points = await db.complete_onboarding(user_id)

    # Логируем
    await db.log_event(
        user_id,
        "onboarding_extended_completed",
        {
            "answers": data.get("answers", {}),
            "demo_learning_done": data.get("demo_learning_done", False),
            "demo_toxic_done": data.get("demo_toxic_done", False),
            "demo_tasks_done": data.get("demo_tasks_done", False),
            "recommended_block": data.get("recommended_block"),
        },
    )

    await state.clear()

    progress = get_onboarding_progress_indicator(OnboardingPhase.COMPLETE)

    # Получаем информацию о рекомендованном блоке, если есть
    recommended_block_id = data.get("recommended_block")
    block_text = ""
    if recommended_block_id:
        lesson_service = container.get_lesson_service()
        block = await lesson_service.get_block(recommended_block_id)
        if block:
            block_text = (
                f"\n\n🎯 Рекомендую начать с блока: <b>{block.emoji} {block.title}</b>"
            )

    text = f"""{progress}

🎉 <b>Поздравляем!</b>

Ты успешно прошёл(ла) знакомство с ботом!

<b>Заработано баллов: +{OnboardingConfig.TOTAL_POINTS}</b>
💎 Всего баллов: <b>{total_points}</b>

<b>🏆 Твоя цель:</b> набрать 1000 баллов
📊 Прогресс: {total_points}/1000{block_text}

<b>Что дальше?</b>
• Пройди первый урок (+50 баллов)
• Попрактикуйся в Toxic Chat (до +30 баллов)
• Не забывай про Daily Insight (+15 баллов ежедневно)

Удачи! 🚀"""

    await callback.message.edit_text(
        text, reply_markup=get_onboarding_complete_keyboard()
    )
    await callback.answer(f"+{OnboardingConfig.TOTAL_POINTS} баллов!")
