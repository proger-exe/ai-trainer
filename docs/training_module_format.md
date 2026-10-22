
# Training Module JSON — документация формата

Этот файл описывает обучающий модуль в формате  
**Блок → Уроки → Шаги**, предназначенный для загрузки в БД или LMS.

---

## Общая структура

```json
{
  "module": {
    "id": "string",
    "title": "string",
    "version": "string",
    "language": "string",
    "created_at": "YYYY-MM-DD",
    "blocks": [Block]
  }
}
````

---

## Module

### Поля

* `id` — уникальный идентификатор модуля
* `title` — название модуля
* `version` — версия (semver)
* `language` — язык контента (`ru`, `en`, …)
* `created_at` — дата создания
* `blocks` — массив блоков

---

## Block

```json
{
  "id": "string",
  "order": 1,
  "title": "string",
  "lessons": [Lesson]
}
```

### Поля

* `id` — уникальный id блока
* `order` — порядок отображения
* `title` — название блока
* `lessons` — массив уроков

---

## Lesson

```json
{
  "id": "string",
  "order": 1,
  "title": "string",
  "duration_min": 10,
  "duration_max": 15,
  "goal": "string | null",
  "status": "stub | null",
  "steps": [Step]
}
```

### Поля

* `id` — уникальный id урока
* `order` — порядок внутри блока
* `title` — название урока
* `duration_min` / `duration_max` — примерная длительность
* `goal` — цель урока (может быть `null`)
* `status`

  * `stub` — урок существует структурно, но контент не заполнен
* `steps` — массив шагов урока

---

## Step (шаг урока)

### Базовая форма

```json
{
  "order": 1,
  "type": "theory",
  "title": "string"
}
```

### Общие поля

* `order` — порядок шага
* `type` — тип шага
* `title` — заголовок шага

---

## Типы шагов и их payload

### 1. Текстовые (`intro`, `theory`, `note`, `example`, `summary`, `rule`)

```json
{
  "type": "theory",
  "title": "Что такое границы",
  "content": "Текст...",
  "cta": { "text": "Далее" }
}
```

---

### 2. Quiz (один правильный ответ)

```json
{
  "type": "quiz_single",
  "title": "Вопрос",
  "prompt": "Что из этого верно?",
  "options": [
    { "id": "A", "text": "Вариант A" },
    { "id": "B", "text": "Вариант B" }
  ],
  "answer": "B"
}
```

Типы:

* `quiz_single`
* `scenario_quiz_single`

---

### 3. Reflection (саморефлексия)

```json
{
  "type": "reflection",
  "title": "Саморефлексия",
  "questions": [
    "В какой ситуации мне сложно сказать «нет»?",
    "Кому мне труднее всего отказывать?"
  ],
  "cta": { "text": "Далее" }
}
```

---

### 4. Toolbox / Lists

```json
{
  "type": "toolbox",
  "title": "Фразы для валидации",
  "items": [
    "Понимаю",
    "Звучит тяжело",
    "Вижу, что тебе это важно"
  ]
}
```

---

### 5. CTA (кнопка)

CTA может присутствовать у любого шага:

```json
"cta": {
  "text": "Далее"
}
```


## Импорт (логика)

1. Создать `module`
2. Для каждого блока → insert `blocks`
3. Для каждого урока → insert `lessons`
4. Для каждого шага:

   * базовые поля → колонки
   * всё остальное → `payload`

---

## Примечания

* Порядок определяется полем `order`, а не позицией в массиве
* `stub`-уроки можно скрывать в UI или помечать как "в разработке"
* Формат стабилен для версионирования и миграций

