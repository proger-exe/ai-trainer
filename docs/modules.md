# Описание модулей

## Core модули

### `core/config.py`
Конфигурация приложения. Хранит настройки из переменных окружения:
- Токены (Telegram, Gemini)
- Пути к файлам
- URL для онбординга

### `core/database.py`
Асинхронная работа с SQLite БД. Класс `AsyncDatabase` предоставляет методы для:
- Инициализации схемы БД
- Работы с пользователями
- Управления баллами
- Логирования событий
- Работы с уроками и тестами

### `core/container.py`
Контейнер зависимостей (DI). Singleton для управления экземплярами:
- База данных
- Репозитории
- Сервисы

### `core/bridge.py`
Мост между компонентами. Позволяет синхронным обработчикам AtlantSDK отправлять сообщения через асинхронный бот.

## Bot модули

### Handlers (`bot/handlers/`)

#### `common.py`
Базовые обработчики:
- `/start` - приветствие
- `/help` - помощь
- Главное меню

#### `webapp.py` ⭐ **НОВЫЙ**
Обработка данных из Telegram WebApp:
- Команда `/test` - доступ к тесту на сайте
- Обработка результатов теста (`quiz_complete`)
- История прохождений теста
- Валидация данных

#### `onboarding.py`
Базовый онбординг через вопросы в боте.

#### `onboarding_extended.py`
Расширенный онбординг с демо-режимами и рекомендациями.

#### `learning.py`
Обработка обучения:
- Просмотр блоков и уроков
- Прохождение уроков
- Прогресс обучения

#### `toxic.py` / `toxic_extended.py`
Toxic Chat - тренировка ответов на токсичные сообщения.

#### `analysis.py`
Разбор ситуаций с помощью AI.

#### `insight.py`
Daily Insight - ежедневные инсайты.

#### `leaderboard.py`
Таблица лидеров по баллам.

#### `admin_panel.py` / `admin/`
Админ-панель для управления:
- Уроками
- Онбордингом
- Пользователями

### Services (`bot/services/`)

#### `supabase_poller.py` ⭐ **НОВЫЙ**
Поллер для проверки новых результатов теста в Supabase:
- Периодическая проверка (интервал 2 сек)
- Отправка уведомлений пользователям
- Сохранение в локальную БД

#### `scheduler.py`
Планировщик задач:
- Ежедневные инсайты
- Напоминания

#### `lesson.py`
Бизнес-логика работы с уроками.

#### `user.py`
Бизнес-логика работы с пользователями.

#### `points.py`
Система баллов.

#### `toxic.py`
Логика Toxic Chat.

#### `onboarding.py`
Логика онбординга.

### Keyboards (`bot/keyboards/`)

Клавиатуры для интерфейса бота:
- `common.py` - общие клавиатуры (главное меню)
- `onboarding_extended.py` - клавиатуры онбординга (включая WebApp)
- `toxic_extended.py` - клавиатуры Toxic Chat
- И другие...

### Repositories (`bot/repositories/`)

Слой доступа к данным:
- `user.py` - пользователи
- `points.py` - баллы
- `lesson.py` - уроки
- И другие...

### Models (`bot/models/`)

Модели данных (Pydantic):
- `user.py`
- `lesson.py`
- `onboarding.py`
- `points.py`
- И другие...

## API модули

### `api_server.py` ⭐ **НОВЫЙ**
HTTP API сервер (aiohttp) для приёма результатов теста с сайта:
- `POST /api/quiz/results` - приём результатов
- `GET /api/health` - проверка работоспособности
- CORS middleware для работы с сайтом
- Интеграция с БД и отправка уведомлений в бот

## Atlant модули

### `atlant/handlers/`
Обработчики для AtlantSDK:
- `analysis.py` - анализ текста
- `toxic.py` - анализ токсичности

### `AtlantSDK/`
SDK для работы с Google Gemini AI:
- Обработка запросов
- Генерация ответов
- Управление моделями

## Deploy модули

### `deploy/`
Скрипты для деплоя:
- `bot.service` - systemd unit файл
- `setup.sh` - скрипт установки на VPS
- `deploy.ps1` - инструкции для Windows

## Взаимодействие модулей

```
User → Handler → Service → Repository → Database
                    ↓
                 AtlantSDK (AI)
                    ↓
                 Response
```

Для онбординга с сайта:
```
Website → API Server → Database → Bot Notification
              ↓
        Supabase (опционально)
              ↓
        Supabase Poller → Database → Bot Notification
```

## Зависимости между модулями

1. **Handlers** зависят от **Services** и **Keyboards**
2. **Services** зависят от **Repositories**
3. **Repositories** зависят от **Database**
4. **Container** управляет всеми зависимостями
5. **Bridge** связывает синхронные и асинхронные компоненты

## Новые модули (после миграции)

⭐ Отмечены новые модули, добавленные при миграции онбординга:
- `api_server.py`
- `bot/services/supabase_poller.py`
- `bot/handlers/webapp.py`
- Обновления в `bot/keyboards/onboarding_extended.py` и `bot/keyboards/common.py`
