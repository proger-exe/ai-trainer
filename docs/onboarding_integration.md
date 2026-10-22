# Интеграция онбординга с сайтом

## Обзор

Система поддерживает два способа прохождения онбординга:
1. **В боте** - через вопросы в Telegram
2. **На сайте** - через WebApp на example.com (15 вопросов)

Результаты с сайта могут поступать двумя путями:
- **Прямой API** - сайт отправляет POST запрос на API сервер
- **Через Supabase** - сайт сохраняет в Supabase, поллер проверяет новые записи

## Архитектура интеграции

```
┌─────────────────┐
│  Сайт           │
│  example.com    │
└────────┬────────┘
         │
         ├─────────────────┐
         │                 │
         ▼                 ▼
┌─────────────────┐  ┌─────────────────┐
│  API Server     │  │   Supabase      │
│  (aiohttp)      │  │   Database      │
│  :8080          │  └────────┬────────┘
└────────┬────────┘           │
         │                    │
         │                    ▼
         │            ┌─────────────────┐
         │            │ Supabase Poller │
         │            └────────┬────────┘
         │                      │
         └──────────┬───────────┘
                    │
                    ▼
            ┌───────────────┐
            │   Database    │
            │   (SQLite)    │
            └───────┬───────┘
                    │
                    ▼
            ┌───────────────┐
            │  Telegram Bot │
            │  Notification │
            └───────────────┘
```

## Компоненты

### 1. API Server (`api_server.py`)

HTTP сервер на порту 8080 для приёма результатов теста.

#### Endpoints

**POST /api/quiz/results**
- Принимает JSON с результатами теста
- Валидирует данные
- Сохраняет в БД
- Отправляет уведомление в бот
- Возвращает JSON ответ

**GET /api/health**
- Проверка работоспособности
- Возвращает `{"status": "ok"}`

#### Формат запроса

```json
{
  "user_id": 123456789,
  "personality_type": "compromising",
  "percentages": {
    "competing": 10,
    "collaborating": 25,
    "compromising": 35,
    "avoiding": 15,
    "accommodating": 15
  },
  "awareness": 7,
  "ras": 5,
  "answers": [...]
}
```

#### Формат ответа

```json
{
  "success": true,
  "points_earned": 50,
  "total_points": 150,
  "message": "Results saved successfully"
}
```

#### CORS

API сервер настроен с CORS headers для работы с сайтом:
- `Access-Control-Allow-Origin: *`
- `Access-Control-Allow-Methods: GET, POST, OPTIONS`
- `Access-Control-Allow-Headers: Content-Type`

### 2. Supabase Poller (`bot/services/supabase_poller.py`)

Фоновый процесс, который периодически проверяет Supabase на наличие новых необработанных результатов.

#### Конфигурация

```python
SUPABASE_URL = 'https://<project>.supabase.co'
SUPABASE_KEY = '...'
```

#### Логика работы

1. Каждые 2 секунды проверяет таблицу `quiz_results` в Supabase
2. Ищет записи с `processed = false`
3. Для каждой записи:
   - Отправляет уведомление пользователю
   - Сохраняет в локальную БД
   - Помечает как обработанную (`processed = true`)

#### Структура таблицы в Supabase

```sql
CREATE TABLE quiz_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    personality_type TEXT,
    percentages JSONB,
    awareness INTEGER,
    ras INTEGER,
    answers JSONB,
    processed BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 3. WebApp Handler (`bot/handlers/webapp.py`)

Обработчик данных из Telegram WebApp.

#### Команды

**/test** - открывает WebApp с тестом на сайте

#### Обработка данных

Обрабатывает сообщения с `web_app_data`:
- `action: "tma_auth"` - авторизация в WebApp (логирование)
- `action: "quiz_complete"` - завершение теста
- `action: "share"` - шаринг результатов

#### Валидация

Проверяет:
- Наличие обязательных полей
- Корректность типа личности
- Диапазоны значений (awareness, ras)
- Подпись initData (опционально)

#### Сохранение результатов

Результаты сохраняются в две таблицы:
- `user_quiz_results` - последний результат (UNIQUE по user_id)
- `user_quiz_history` - история всех прохождений

### 4. Клавиатуры

#### `get_onboarding_welcome_keyboard(user_id)`
Клавиатура приветствия онбординга. Если настроен `ONBOARDING_WEBAPP_URL`, показывает кнопку WebApp вместо обычной кнопки.

#### `get_webapp_results_keyboard()`
Клавиатура после прохождения теста в WebApp.

#### `get_main_keyboard(show_test_button)`
Главное меню с опциональной кнопкой теста.

## База данных

### Таблицы для онбординга

#### `user_quiz_results`
Последний результат теста пользователя:

```sql
CREATE TABLE user_quiz_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE,
    personality_type TEXT,
    percentages TEXT,  -- JSON
    awareness INTEGER,
    ras INTEGER,
    answers TEXT,  -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

#### `user_quiz_history`
История всех прохождений теста:

```sql
CREATE TABLE user_quiz_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    personality_type TEXT,
    percentages TEXT,  -- JSON
    awareness INTEGER,
    ras INTEGER,
    answers TEXT,  -- JSON
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## Типы личности

Система определяет 5 типов стратегий поведения:

- `competing` - Конкуренция 🦈
- `collaborating` - Сотрудничество 🦉
- `compromising` - Компромисс 🦊
- `avoiding` - Избегание 🐢
- `accommodating` - Адаптивность 🧸

## Логика начисления баллов

- **Первое прохождение**: +50 баллов (`PointsConfig.ONBOARDING_COMPLETE`)
- **Повторное прохождение**: баллы не начисляются, только обновление результатов

## Уведомления

После прохождения теста пользователь получает уведомление в бот с:
- Результатами теста (стратегия, осознанность, ассертивность)
- Начисленными баллами (если первое прохождение)
- Кнопками для дальнейших действий

## Конфигурация

### Переменные окружения

```env
# URL теста на сайте (для WebApp)
ONBOARDING_WEBAPP_URL=https://example.com/test?user_id=

# Токены (обязательные)
TELEGRAM_BOT_TOKEN=...
GEMINI_API_TOKEN=...
```

### Настройка API сервера

По умолчанию API сервер запускается на:
- Host: `0.0.0.0` (все интерфейсы)
- Port: `8080`

Можно изменить в `main.py`:
```python
api_runner = await start_api_server(bot, host="0.0.0.0", port=8080)
```

## Безопасность

1. **Валидация данных** - проверка всех входящих данных
2. **CORS** - настройка заголовков для работы с сайтом
3. **Подпись WebApp** - опциональная проверка подписи initData
4. **Логирование** - все события логируются для аналитики

## Тестирование

### Локальный тест API

```bash
curl -X POST http://localhost:8080/api/quiz/results \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": 123456789,
    "personality_type": "compromising",
    "percentages": {"competing": 10, "collaborating": 20, "compromising": 40, "avoiding": 15, "accommodating": 15},
    "awareness": 7,
    "ras": 5,
    "answers": []
  }'
```

### Health check

```bash
curl http://localhost:8080/api/health
# {"status": "ok"}
```

## Troubleshooting

### API сервер не запускается
- Проверьте, что порт 8080 свободен
- Проверьте логи в консоли

### Supabase поллер не работает
- Проверьте подключение к интернету
- Проверьте правильность URL и ключа Supabase
- Проверьте логи на наличие ошибок

### WebApp не открывается
- Проверьте, что `ONBOARDING_WEBAPP_URL` настроен в `.env`
- Проверьте, что URL корректный и доступен

### Результаты не сохраняются
- Проверьте логи на наличие ошибок
- Проверьте структуру БД
- Проверьте права доступа к файлу БД
