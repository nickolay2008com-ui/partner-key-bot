# Railway Postgres: что сделать после создания базы

Короткий чеклист, чтобы бот реально начал писать профили, историю разборов и Web App данные в Railway Postgres, а не во временный SQLite внутри контейнера.

## 1. Подключить базу к сервису бота

В Railway открой сервис `partner-key-bot` → `Variables` и добавь переменную:

```text
DATABASE_URL=${{Postgres-L0sw.DATABASE_URL}}
```

Если имя Postgres-сервиса отличается, выбери его через Railway variable reference picker. Для связи сервис-в-сервис внутри одного проекта нужен именно внутренний `DATABASE_URL`, а публичный TCP URL нужен только для внешних клиентов.

## 2. Проверить обязательные переменные

Минимальный production-набор для текущего бота:

```text
TELEGRAM_BOT_TOKEN=токен_из_BotFather
DATABASE_URL=${{Postgres-L0sw.DATABASE_URL}}
WEBAPP_URL=https://partner-key.up.railway.app/webapp
APP_TIMEZONE=Europe/Moscow
```

Опционально:

```text
AUTHORIZED_TELEGRAM_IDS=123456789
BROADCAST_ADMIN_IDS=123456789
```

## 3. Redeploy сервиса бота

После добавления `DATABASE_URL` запусти redeploy `partner-key-bot`. На старте приложение само создаёт таблицы:

- `partner_reports` — сохранённые разборы;
- `bot_users` — пользователи для истории/рассылок;
- `broadcast_log` — защита от повторных рассылок;
- `user_profiles` — данные из Telegram Web App.

## 4. Проверить healthcheck

Открой:

```text
https://partner-key.up.railway.app/healthz
```

Рабочий Postgres-режим должен вернуть примерно:

```json
{"ok": true, "storage": {"ok": true, "storage": "postgres"}}
```

Если видишь `storage: sqlite`, значит `DATABASE_URL` не попал в переменные именно сервиса бота или сервис ещё не redeploy-нулся.

## 5. Проверить пользовательский сценарий

1. В Telegram отправь `/start`.
2. Нажми `👤 Мои данные` и сохрани свои данные + данные партнёра.
3. Запусти `💞 Начать разбор пары`.
4. Проверь, что бот предлагает использовать данные из профиля.
5. Сделай разбор и открой `🗂 История`.

Если профиль и история сохраняются после redeploy — рабочий функционал подключён к базе корректно.

## 6. Что улучшить следующим MVP-шагом

Чтобы продукт не был «просто ботом с базой», следующий дешёвый рычаг — добавить события воронки:

- `start_opened`;
- `profile_saved`;
- `partner_report_created`;
- `bridge_created`;
- `message_hint_clicked`.

Это покажет, где пользователи отваливаются: до профиля, после первого разбора или перед глубокими блоками.
