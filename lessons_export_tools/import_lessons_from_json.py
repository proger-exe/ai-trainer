#!/usr/bin/env python3
"""
Скрипт для импорта уроков из lessons.json в базу данных
"""

import json
import asyncio
import aiosqlite
import re
from typing import Dict, List, Optional, Tuple
from core.config import Config


def extract_correct_answer(
    explanation_content: str, quiz_options: List[Dict]
) -> Optional[str]:
    """Извлечение правильного ответа из explanation"""
    if not explanation_content:
        return None

    # Маппинг букв на цифры (A=1, B=2, C=3, D=4)
    letter_to_number = {"A": "1", "B": "2", "C": "3", "D": "4"}

    # Ищем паттерны типа "Правильный ответ: C", "Ответ: C", "C", "Вариант C"
    patterns = [
        r"Правильный ответ:\s*([A-Z0-9]+)",
        r"Ответ:\s*([A-Z0-9]+)",
        r"Вариант\s+([A-Z0-9]+)",
        r"^([A-Z0-9]+)\.",  # Начало строки с буквой/цифрой
        r"ответ:\s*([A-Z0-9]+)",  # С маленькой буквы
    ]

    for pattern in patterns:
        match = re.search(pattern, explanation_content, re.IGNORECASE | re.MULTILINE)
        if match:
            answer_id = match.group(1).strip().upper()

            # Находим текст варианта по ID
            for option in quiz_options:
                opt_id = str(option.get("id", "")).strip().upper()
                # Прямое совпадение
                if opt_id == answer_id:
                    answer_text = clean_text(option.get("text", ""))
                    answer_text = answer_text.strip('«»""')
                    if answer_text:
                        return answer_text

                # Если answer_id - буква, а opt_id - цифра, проверяем маппинг
                if (
                    answer_id in letter_to_number
                    and opt_id == letter_to_number[answer_id]
                ):
                    answer_text = clean_text(option.get("text", ""))
                    answer_text = answer_text.strip('«»""')
                    if answer_text:
                        return answer_text

                # Обратный маппинг: если answer_id - цифра, а opt_id - буква
                for letter, number in letter_to_number.items():
                    if answer_id == number and opt_id == letter:
                        answer_text = clean_text(option.get("text", ""))
                        answer_text = answer_text.strip('«»""')
                        if answer_text:
                            return answer_text

            # Если не нашли текст, возвращаем None
            return None

    return None


def get_emoji_for_block(title: str) -> str:
    """Получение эмодзи для блока по названию"""
    emoji_map = {
        "Границы": "🛡️",
        "Манипуляции и агрессия": "⚠️",
        "Переговоры": "🤝",
    }
    return emoji_map.get(title, "📚")


def should_skip_step(step: Dict) -> bool:
    """Проверка, нужно ли пропустить шаг"""
    step_type = step.get("type", "")

    # Пропускаем пустые или мусорные шаги
    if step_type == "content" and not step.get("content") and not step.get("title"):
        return True

    # Пропускаем шаги-заглушки
    if step.get("status") == "stub":
        return True

    # Пропускаем пустые шаги без контента
    if not step.get("content") and not step.get("title") and not step.get("prompt"):
        return True

    return False


def clean_text(text: str) -> str:
    """Очистка текста от мусора"""
    if not text:
        return text
    # Убираем лишние фразы
    text = text.replace("Текст на кнопке: Выбери вариант ответа", "")
    text = text.replace("Текст на кнопке:", "")
    text = text.strip()
    return text


def format_fragment_content(step: Dict) -> str:
    """Форматирование контента фрагмента из шага"""
    parts = []

    if step.get("title"):
        parts.append(f"<b>{step['title']}</b>")

    if step.get("content"):
        content = step["content"].strip()
        # Заменяем маркдаун на HTML где нужно
        content = content.replace("\n\n", "\n")
        parts.append(content)

    if step.get("prompt"):
        parts.append(f"\n<b>Вопрос:</b> {step['prompt']}")

    if step.get("options"):
        options_text = []
        for opt in step["options"]:
            opt_id = opt.get("id", "")
            opt_text = clean_text(opt.get("text", ""))
            options_text.append(f"{opt_id}. {opt_text}")
        if options_text:
            parts.append("\n" + "\n".join(options_text))

    return "\n\n".join(parts).strip()


async def import_lessons():
    """Импорт уроков из JSON в БД"""
    # Инициализируем БД
    from core.database import AsyncDatabase

    db = AsyncDatabase(Config.DATABASE_PATH)
    await db.init_db()

    db_path = Config.DATABASE_PATH

    # Читаем JSON
    with open("lessons.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    module = data.get("module", {})
    blocks_data = module.get("blocks", [])

    async with aiosqlite.connect(db_path) as conn:
        # Очищаем существующие данные (опционально)
        await conn.execute("DELETE FROM fragments")
        await conn.execute("DELETE FROM lessons")
        await conn.execute("DELETE FROM blocks")
        await conn.commit()

        block_id_map = {}  # Маппинг старых ID на новые

        # Обрабатываем блоки
        for block_data in blocks_data:
            block_title = block_data.get("title", "")
            block_order = block_data.get("order", 0)
            block_emoji = get_emoji_for_block(block_title)

            # Вставляем блок
            cursor = await conn.execute(
                """
                INSERT INTO blocks (title, emoji, description, "order", is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """,
                (block_title, block_emoji, None, block_order, 1),
            )

            new_block_id = cursor.lastrowid
            block_id_map[block_data.get("id")] = new_block_id
            await conn.commit()

            print(f"✓ Блок создан: {block_title} (ID: {new_block_id})")

            # Обрабатываем уроки блока
            lessons_data = block_data.get("lessons", [])
            lesson_id_map = {}  # Маппинг старых ID уроков на новые

            for lesson_data in lessons_data:
                # Пропускаем заглушки
                if lesson_data.get("status") == "stub":
                    print(f"  ⏭ Пропущен урок-заглушка: {lesson_data.get('title')}")
                    continue

                lesson_title = lesson_data.get("title", "")
                lesson_order = lesson_data.get("order", 0)

                # Вставляем урок
                cursor = await conn.execute(
                    """
                    INSERT INTO lessons (block_id, title, "order", is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
                """,
                    (new_block_id, lesson_title, lesson_order, 1),
                )

                new_lesson_id = cursor.lastrowid
                lesson_id_map[lesson_data.get("id")] = new_lesson_id
                await conn.commit()

                print(f"  ✓ Урок создан: {lesson_title} (ID: {new_lesson_id})")

                # Обрабатываем шаги урока
                steps = lesson_data.get("steps", [])
                fragments_to_insert = []

                i = 0
                while i < len(steps):
                    step = steps[i]

                    # Пропускаем мусорные шаги
                    if should_skip_step(step):
                        i += 1
                        continue

                    step_type = step.get("type", "")

                    # Обрабатываем тесты
                    if step_type in ["quiz_single", "scenario_quiz_single"]:
                        # Формируем контент теста
                        test_content = format_fragment_content(step)
                        quiz_options = step.get("options", [])

                        # Ищем правильный ответ в следующем explanation
                        correct_answer = None
                        explanation_used = False
                        # Проверяем следующие 3 шага на случай, если между ними есть что-то
                        for j in range(1, min(4, len(steps) - i)):
                            if i + j < len(steps):
                                next_step = steps[i + j]
                                if next_step.get("type") == "explanation":
                                    explanation_content = next_step.get("content", "")
                                    correct_answer = extract_correct_answer(
                                        explanation_content, quiz_options
                                    )
                                    # Если нашли ответ, пропускаем explanation (он уже использован)
                                    if correct_answer:
                                        explanation_used = True
                                        i += j  # Пропускаем все шаги до explanation включительно
                                        break

                        # Если не нашли ответ из explanation, пытаемся определить по контексту
                        if not correct_answer and quiz_options:
                            # Логика определения правильного ответа по контексту урока
                            # Ищем вариант с "я-сообщением" или про границы
                            for opt in quiz_options:
                                opt_text = opt.get("text", "").lower()
                                # Признаки правильного ответа:
                                # - содержит "мне", "я", "мои" (я-сообщение)
                                # - содержит "границы", "важно", "обсудить", "договориться"
                                # - НЕ содержит обвинений, агрессии, ультиматумов
                                if any(
                                    word in opt_text
                                    for word in [
                                        "мне",
                                        "я",
                                        "мои",
                                        "важно",
                                        "обсудить",
                                        "договориться",
                                        "неловко",
                                    ]
                                ):
                                    bad_words = [
                                        "ты должен",
                                        "ты обязан",
                                        "перестань",
                                        "ненавижу",
                                        "ужасно",
                                    ]
                                    if not any(
                                        bad_word in opt_text for bad_word in bad_words
                                    ):
                                        correct_answer = clean_text(opt.get("text", ""))
                                        break

                            # Если не нашли по логике, используем эвристики
                            if not correct_answer and len(quiz_options) > 0:
                                # Для тестов с 2 вариантами обычно правильный - второй (более конструктивный)
                                if len(quiz_options) == 2:
                                    correct_answer = clean_text(
                                        quiz_options[1].get("text", "")
                                    )
                                # Для тестов с 3 вариантами обычно правильный - третий
                                elif len(quiz_options) == 3:
                                    correct_answer = clean_text(
                                        quiz_options[2].get("text", "")
                                    )
                                # Для тестов с 4 вариантами обычно правильный - третий (C) или второй (B)
                                elif len(quiz_options) == 4:
                                    # Сначала пробуем C
                                    for opt in quiz_options:
                                        if opt.get("id", "").upper() == "C":
                                            correct_answer = clean_text(
                                                opt.get("text", "")
                                            )
                                            break
                                    # Если не нашли C, пробуем B
                                    if not correct_answer:
                                        for opt in quiz_options:
                                            if opt.get("id", "").upper() == "B":
                                                correct_answer = clean_text(
                                                    opt.get("text", "")
                                                )
                                                break
                                    # Если все еще не нашли, берем второй вариант
                                    if not correct_answer and len(quiz_options) >= 2:
                                        correct_answer = clean_text(
                                            quiz_options[1].get("text", "")
                                        )

                        # Если все еще не нашли, пропускаем тест
                        if not correct_answer:
                            print(
                                f"    ⚠️ ВНИМАНИЕ: Не найден правильный ответ для теста в уроке '{lesson_title}' (шаг {step.get('order')})"
                            )
                            i += 1
                            continue

                        # Очищаем ответ от мусора
                        correct_answer = clean_text(correct_answer)

                        # Находим ID правильного ответа
                        correct_answer_id = None

                        # Сначала пытаемся найти ID по тексту ответа
                        for opt in quiz_options:
                            opt_text = clean_text(opt.get("text", ""))
                            if opt_text.lower() == correct_answer.lower():
                                correct_answer_id = (
                                    str(opt.get("id", "")).strip().upper()
                                )
                                break

                        # Если не нашли ID по тексту, извлекаем из explanation
                        if not correct_answer_id:
                            # Ищем в explanation упоминание правильного ответа
                            if i + 1 < len(steps):
                                next_step = steps[i + 1]
                                if next_step.get("type") == "explanation":
                                    explanation_content = next_step.get("content", "")
                                    # Извлекаем ID из explanation
                                    patterns = [
                                        r"Правильный ответ:\s*([A-Z0-9]+)",
                                        r"Ответ:\s*([A-Z0-9]+)",
                                    ]
                                    for pattern in patterns:
                                        match = re.search(
                                            pattern, explanation_content, re.IGNORECASE
                                        )
                                        if match:
                                            correct_answer_id = (
                                                match.group(1).strip().upper()
                                            )
                                            break

                        # Если все еще не нашли, используем эвристики
                        if not correct_answer_id and quiz_options:
                            # Для тестов с 2 вариантами обычно правильный - второй
                            if len(quiz_options) == 2:
                                correct_answer_id = (
                                    str(quiz_options[1].get("id", "")).strip().upper()
                                )
                            # Для тестов с 3 вариантами обычно правильный - третий
                            elif len(quiz_options) == 3:
                                correct_answer_id = (
                                    str(quiz_options[2].get("id", "")).strip().upper()
                                )
                            # Для тестов с 4 вариантами обычно правильный - третий (C)
                            elif len(quiz_options) == 4:
                                for opt in quiz_options:
                                    if opt.get("id", "").upper() == "C":
                                        correct_answer_id = "C"
                                        break
                                if not correct_answer_id:
                                    correct_answer_id = (
                                        str(quiz_options[1].get("id", ""))
                                        .strip()
                                        .upper()
                                    )

                        # Сохраняем ТОЛЬКО ID правильного ответа (C, 3 и т.д.)
                        fragments_to_insert.append(
                            {
                                "lesson_id": new_lesson_id,
                                "fragment_type": "test",
                                "content": test_content,
                                "correct_answer": correct_answer_id or "",
                                "order": len(fragments_to_insert),
                            }
                        )

                    # Обрабатываем теорию (все остальные типы)
                    elif step_type in [
                        "intro",
                        "theory",
                        "content",
                        "note",
                        "example",
                        "reflection",
                        "summary",
                        "toolbox",
                        "rule",
                    ]:
                        content = format_fragment_content(step)
                        if content:  # Только если есть контент
                            fragments_to_insert.append(
                                {
                                    "lesson_id": new_lesson_id,
                                    "fragment_type": "theory",
                                    "content": content,
                                    "correct_answer": None,
                                    "order": len(fragments_to_insert),
                                }
                            )

                    # explanation пропускаем (уже обработан с тестом)
                    elif step_type == "explanation":
                        pass  # Уже обработано выше

                    i += 1

                # Вставляем фрагменты
                for frag in fragments_to_insert:
                    await conn.execute(
                        """
                        INSERT INTO fragments (lesson_id, fragment_type, content, correct_answer, "order", created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, datetime('now'), datetime('now'))
                    """,
                        (
                            frag["lesson_id"],
                            frag["fragment_type"],
                            frag["content"],
                            frag["correct_answer"],
                            frag["order"],
                        ),
                    )

                await conn.commit()
                print(f"    ✓ Создано фрагментов: {len(fragments_to_insert)}")

        print("\n✅ Импорт завершен!")


if __name__ == "__main__":
    asyncio.run(import_lessons())
