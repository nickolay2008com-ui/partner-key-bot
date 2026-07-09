# Partner Key Bot

Telegram-бот для мягкого разбора эмоционального языка партнёра по дате рождения и построения карты гармонии пары.

## Что внутри

- Telegram long polling бот на `python-telegram-bot`.
- Расчёт астрологических показателей через Swiss Ephemeris.
- Локальное SQLite-хранилище истории, пользователей и профилей.
- Telegram Web App для сохранения данных пользователя и партнёра.
- Опциональная генерация текстов через OpenAI API.

## Запуск локально

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m app.woman_flow
```

Минимально нужен `TELEGRAM_BOT_TOKEN` в `.env`.

## Переменные окружения

| Переменная | Обязательна | Описание |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | да | Токен Telegram-бота. |
| `AUTHORIZED_TELEGRAM_IDS` | нет | Список разрешённых Telegram ID через запятую. Пусто = публичный доступ. |
| `BROADCAST_ADMIN_IDS` | нет | Админы служебных рассылок через запятую. |
| `APP_TIMEZONE` | нет | Таймзона приложения, по умолчанию `Europe/Moscow`. |
| `DATA_DIR` | нет | Папка для SQLite-файла. Если не задана, на Railway автоматически используется `RAILWAY_VOLUME_MOUNT_PATH`, иначе `data`. |
| `WEBAPP_URL` | нет | Публичный URL мини-приложения Telegram Web App. |
| `OPENAI_API_KEY` | нет | Ключ OpenAI для улучшения вариантов сообщений. |
| `OPENAI_MODEL` | нет | Модель OpenAI, по умолчанию `gpt-4.1-mini`. |

## Production

Для сохранения профиля и истории после рестарта подключите Railway Volume. Код выбирает папку для SQLite так:

1. `DATA_DIR`, если переменная задана явно;
2. `RAILWAY_VOLUME_MOUNT_PATH`, если Railway передал путь volume;
3. `/data` на Railway, чтобы стандартный volume с mount path `/data` работал без дополнительной переменной;
4. локально — `data`.

Важно: если Railway Volume не подключён к выбранному пути, SQLite-файл остаётся внутри контейнера и будет потерян при redeploy/restart. Для production подключите Volume и укажите mount path `/data` или задайте `DATA_DIR` равным mount path.

Docker-образ стартует основной сценарий через Railway-команду:

```bash
python -m app.woman_flow
```

Веб-приложение поднимается внутри процесса на `PORT` и отдаёт:

- `/healthz` — healthcheck;
- `/webapp` — Telegram Web App;
- `/api/profile` — профиль пользователя.

## Проверки

```bash
python -m ruff check app
python -m ruff format --check app
python -m compileall app
```
