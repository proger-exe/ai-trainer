"""
Миграция: перенос вопросов онбординга из константы в БД
"""

import asyncio
import aiosqlite
from core.config import Config
from core.database import AsyncDatabase
from bot.repositories.onboarding import OnboardingQuestionRepository
from bot.models.onboarding import OnboardingQuestionCreate

# Вопросы из константы (для миграции)
ONBOARDING_QUESTIONS_DATA = [
    {
        "key": "main_challenge",
        "title": "Вопрос 1 из 5 🎯",
        "content": "С какой ситуацией ты чаще всего сталкиваешься?",
        "options": [
            "🛡️ Сложно отстаивать свои границы",
            "🎭 Чувствую, что мной манипулируют",
            "🤝 Не получается договариваться",
            "😤 Встречаю агрессию и токсичность",
        ],
        "order": 0,
    },
    {
        "key": "conflict_reaction",
        "title": "Вопрос 2 из 5 💭",
        "content": "Как ты обычно реагируешь на конфликт?",
        "options": [
            "😶 Избегаю и молчу",
            "😠 Иду в атаку",
            "😔 Уступаю, чтобы не ссориться",
            "🗣️ Пытаюсь обсудить спокойно",
        ],
        "order": 1,
    },
    {
        "key": "experience_level",
        "title": "Вопрос 3 из 5 📊",
        "content": "Как бы ты оценил(а) свои навыки коммуникации?",
        "options": [
            "🌱 Начинающий — часто теряюсь",
            "📈 Средний — иногда справляюсь",
            "💪 Продвинутый — обычно справляюсь",
            "🎓 Эксперт — хочу отточить навыки",
        ],
        "order": 2,
    },
    {
        "key": "priority_area",
        "title": "Вопрос 4 из 5 🎯",
        "content": "Какая сфера для тебя сейчас наиболее важна?",
        "options": [
            "💼 Работа и карьера",
            "❤️ Личные отношения",
            "👨‍👩‍👧 Семья и родственники",
            "👥 Друзья и знакомые",
        ],
        "order": 3,
    },
    {
        "key": "time_commitment",
        "title": "Вопрос 5 из 5 ⏰",
        "content": "Сколько времени готов(а) уделять обучению?",
        "options": [
            "⚡ 5 минут в день",
            "📖 15-20 минут в день",
            "📚 Когда будет время",
            "🎯 Хочу пройти всё быстро",
        ],
        "order": 4,
    },
]


async def migrate():
    """Перенос вопросов онбординга в БД"""
    db = AsyncDatabase(Config.DATABASE_PATH)
    await db.init_db()

    repo = OnboardingQuestionRepository(db)

    # Проверяем, есть ли уже вопросы в БД
    existing_questions = await repo.get_all(include_inactive=True)
    if existing_questions:
        print(
            f"⚠️  В БД уже есть {len(existing_questions)} вопросов. Пропускаем миграцию."
        )
        return

    print("🔄 Начинаю миграцию вопросов онбординга...")

    for question_data in ONBOARDING_QUESTIONS_DATA:
        try:
            # Преобразуем ключ "key" в "question_key"
            question_dict = question_data.copy()
            question_dict["question_key"] = question_dict.pop("key")
            question = OnboardingQuestionCreate(**question_dict)
            created = await repo.create(question)
            print(f"✅ Создан вопрос: {created.question_key} - {created.title}")
        except Exception as e:
            print(
                f"❌ Ошибка при создании вопроса {question_data.get('key', 'unknown')}: {e}"
            )

    print(f"✅ Миграция завершена! Создано {len(ONBOARDING_QUESTIONS_DATA)} вопросов.")


if __name__ == "__main__":
    asyncio.run(migrate())
