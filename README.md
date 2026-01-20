# Telegram Bot for Channel Publications

Телеграм-бот для создания и автоматической публикации постов в канал.

## Стек технологий

- **Python 3.11**
- **aiogram 3** — асинхронный фреймворк для Telegram Bot API
- **PostgreSQL** — база данных
- **SQLAlchemy 2 (async)** — ORM
- **Alembic** — миграции базы данных
- **APScheduler** — планировщик задач для отложенной публикации
- **Pydantic Settings** — управление конфигурацией
- **Docker & Docker Compose** — контейнеризация

## Структура проекта

```
bot-posts/
├── app/
│   ├── __init__.py
│   ├── main.py              # Entrypoint
│   ├── config.py            # Конфигурация (pydantic-settings)
│   ├── logging_config.py    # Настройка логов
│   ├── bot.py               # Инициализация Bot/Dispatcher
│   ├── db/
│   │   ├── base.py          # Declarative Base
│   │   ├── session.py       # Async session factory
│   │   ├── models.py        # Модели: DraftPost, DraftMedia, DraftButton
│   │   └── repo.py          # Репозитории
│   ├── routers/
│   │   ├── common.py        # /start, /help, /cancel
│   │   ├── post_wizard.py   # FSM создания поста
│   │   ├── drafts.py        # Список черновиков
│   │   └── edit_published.py
│   ├── services/
│   │   ├── scheduler.py     # APScheduler интеграция
│   │   ├── publishing.py    # Публикация в канал
│   │   ├── preview.py       # Превью в личку
│   │   ├── datetime_parse.py # Парсер даты/времени
│   │   ├── permissions.py   # Проверка прав
│   │   └── media_group.py   # Сбор альбомов
│   ├── keyboards/
│   │   ├── inline.py
│   │   └── reply.py
│   ├── middlewares/
│   │   └── admin_only.py    # Ограничение доступа
│   └── utils/
│       ├── errors.py
│       └── telegram.py
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── tests/
│   ├── conftest.py
│   └── test_repo.py
├── .env.example
├── alembic.ini
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── README.md
```

## Быстрый старт

### 1. Создание .env файла

Скопируйте `.env.example` в `.env` и заполните значения:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN=1234567890:ABCDefghIJKlmnoPQRstuvWXYz

# ID канала для публикаций
CHANNEL_ID=-1001234567890

# ID администраторов бота (через запятую)
ADMIN_IDS=123456789,987654321

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=botuser
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=bot_posts

# Уровень логирования
LOG_LEVEL=INFO

# Часовой пояс
TZ=Europe/Moscow
```

### 2. Как получить BOT_TOKEN

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен в `BOT_TOKEN`

### 3. Как получить CHANNEL_ID

**Способ 1 — для публичных каналов:**
- Используйте username канала: `@your_channel`

**Способ 2 — для приватных каналов:**
1. Откройте [@userinfobot](https://t.me/userinfobot) или [@getidsbot](https://t.me/getidsbot)
2. Перешлите любое сообщение из вашего канала в бот
3. Бот покажет ID канала (начинается с `-100`)

**Способ 3 — через веб-версию:**
1. Откройте канал в [web.telegram.org](https://web.telegram.org)
2. В URL будет ID: `https://web.telegram.org/a/#-1001234567890`
3. ID канала: `-1001234567890`

### 4. Добавление бота администратором в канал

1. Откройте настройки канала
2. Перейдите в **Администраторы** → **Добавить администратора**
3. Найдите вашего бота по username
4. **Обязательно включите права:**
   - ✅ Публикация сообщений (Post messages)
   - ✅ Редактирование сообщений (Edit messages)
   - ✅ Удаление сообщений (Delete messages) — опционально

### 5. Как получить ADMIN_IDS

1. Откройте [@userinfobot](https://t.me/userinfobot)
2. Отправьте любое сообщение
3. Бот покажет ваш User ID
4. Добавьте ID в `ADMIN_IDS` (через запятую для нескольких)

## Запуск

### Локальный запуск (development)

```bash
# Установить зависимости через Poetry
poetry install

# Или через pip
pip install -r requirements.txt

# Накатить миграции
alembic upgrade head

# Запустить бота
python -m app.main
```

### Запуск в Docker

```bash
# Сборка и запуск
docker compose up -d --build

# Просмотр логов
docker compose logs -f bot

# Остановка
docker compose down
```

## Миграции базы данных

### Создание новой миграции

```bash
# Автогенерация на основе изменений в моделях
alembic revision --autogenerate -m "description"

# Ручное создание
alembic revision -m "description"
```

### Применение миграций

```bash
# Применить все миграции
alembic upgrade head

# Откатить последнюю миграцию
alembic downgrade -1

# Посмотреть текущую версию
alembic current

# Посмотреть историю миграций
alembic history
```

### Миграции в Docker

```bash
# Выполнить миграции внутри контейнера
docker compose exec bot alembic upgrade head
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и меню |
| `/new` | Создать новый пост |
| `/drafts` | Список черновиков |
| `/help` | Справка |
| `/cancel` | Отмена текущего действия |

## Тестирование

```bash
# Запуск тестов
pytest

# С покрытием
pytest --cov=app

# Только асинхронные тесты
pytest -m asyncio
```

## Разработка

### Добавление новых зависимостей

```bash
# Через Poetry
poetry add package_name

# Dev-зависимости
poetry add --group dev package_name
```

### Линтинг

```bash
# Проверка типов
mypy app

# Форматирование
black app tests
isort app tests

# Линтинг
ruff check app tests
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|------------|----------|--------------|
| `BOT_TOKEN` | Токен Telegram бота | — |
| `CHANNEL_ID` | ID канала для публикаций | — |
| `ADMIN_IDS` | ID администраторов (через запятую) | — |
| `POSTGRES_HOST` | Хост PostgreSQL | `localhost` |
| `POSTGRES_PORT` | Порт PostgreSQL | `5432` |
| `POSTGRES_USER` | Пользователь БД | `botuser` |
| `POSTGRES_PASSWORD` | Пароль БД | — |
| `POSTGRES_DB` | Имя базы данных | `bot_posts` |
| `LOG_LEVEL` | Уровень логирования | `INFO` |
| `TZ` | Часовой пояс | `Europe/Moscow` |

## Лицензия

MIT
