# AI Trainer

<!-- portfolio-card:start -->
[![AI Trainer — Практика общения: от урока до разбора ситуации.](docs/portfolio/card.png)](docs/portfolio/card.svg)
<!-- portfolio-card:end -->

Учебный курс, который проходит внутри Telegram: короткие шаги, вопросы для проверки и разбор ситуации, которую описал сам пользователь. AI Trainer соединяет структурированные уроки с ответами языковой модели.

Участник проходит вводный опрос, получает задания и накапливает прогресс. Автор курса загружает содержание из JSON; администратор управляет пользователями и рассылками.

## От содержания курса до практики

- Уроки организованы как блоки, уроки и шаги. Формат описан в `docs/training_module_format.md`; сервисы сохраняют прогресс, баллы и инсайты.
- Вводный опрос из 15 вопросов можно пройти в боте или WebApp на сайте. Результаты возвращаются через REST API либо Supabase poller.
- Для разбора ситуаций и токсичных формулировок используются отдельные промпты `models/analysis.md` и `models/toxic.md`, вызовы проходят через AtlantSDK.
- Планировщик отправляет напоминания; инструменты в `lessons_export_tools/` помогают импортировать учебные модули.

Проект показывает, как связать контент, пользовательский прогресс и LLM в одном продукте. HTTP API на aiohttp обслуживает результаты опроса и поиск пользователей с ограничением частоты запросов по IP.

Обсудить похожий проект: [sh3l.beer](https://sh3l.beer).

## Стек

Python 3.11+, aiogram 3.13, aiohttp, aiosqlite, pydantic 2 и google-generativeai. Данные хранятся в SQLite. Бот, API и poller работают в одном процессе; Docker для запуска не требуется. AtlantSDK маршрутизирует LLM-вызовы через обработчики, фильтры и приоритеты с CAS-защитой сессий.

## Запуск

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env     # TELEGRAM_BOT_TOKEN, GEMINI_API_TOKEN, ADMIN_IDS
.venv/bin/python main.py
```

Импорт учебного модуля:

```bash
.venv/bin/python -m lessons_export_tools.import_lessons_from_json lessons_export_tools/lessons.json
```

Для развёртывания на сервере предусмотрены `deploy/setup.sh` и systemd-unit `deploy/bot.service`.

## Структура проекта

```
main.py                  entry point: bot + API server + poller
api_server.py            aiohttp API with rate limiting
core/                    config, async SQLite, DI container, bot<->LLM bridge
bot/                     aiogram handlers, keyboards, FSM states, services, repositories
atlant/                  LLM-side routers and handlers (analysis, toxicity)
AtlantSDK/               LLM dispatcher library (routers, filters, model registry)
models/, models.json     system prompts and model registry
lessons_export_tools/    lesson JSON + import / migration scripts
docs/                    architecture, modules, onboarding integration, lesson format
```

## Лицензия

MIT
