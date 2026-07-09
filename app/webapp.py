from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlparse

from app.config import settings
from app.storage import ReportsStore

logger = logging.getLogger(__name__)
_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path, settings.database_url)
    return _store


def _validate_init_data(init_data: str) -> int:
    if not init_data:
        raise ValueError("Откройте это окно из Telegram, чтобы бот понял, кто вы.")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise ValueError("Telegram не передал подпись авторизации.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Не удалось подтвердить Telegram-пользователя.")

    raw_user = pairs.get("user")
    if not raw_user:
        raise ValueError("Telegram не передал пользователя.")
    user = json.loads(raw_user)
    user_id = int(user["id"])
    return user_id


WEBAPP_HTML = """<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <script src="https://telegram.org/js/telegram-web-app.js"></script>
  <title>Мои данные</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: var(--tg-theme-bg-color, #101014);
      --card: var(--tg-theme-secondary-bg-color, #1b1b22);
      --text: var(--tg-theme-text-color, #f4f4f5);
      --hint: var(--tg-theme-hint-color, #9ca3af);
      --button: var(--tg-theme-button-color, #7c3aed);
      --button-text: var(--tg-theme-button-text-color, #ffffff);
      --border: rgba(255, 255, 255, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 18px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    h1 { font-size: 24px; margin: 0 0 8px; }
    p { margin: 0 0 18px; color: var(--hint); line-height: 1.45; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 16px;
      margin-bottom: 14px;
    }
    .title { font-weight: 700; margin-bottom: 12px; }
    label { display: block; font-size: 14px; color: var(--hint); margin: 12px 0 6px; }
    input {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 13px 14px;
      background: rgba(255,255,255,0.06);
      color: var(--text);
      font-size: 16px;
      outline: none;
    }
    input:focus { border-color: var(--button); }
    .row { display: grid; gap: 12px; }
    button {
      width: 100%;
      border: none;
      border-radius: 16px;
      padding: 14px 16px;
      font-size: 16px;
      font-weight: 700;
      background: var(--button);
      color: var(--button-text);
      margin-top: 8px;
    }
    .secondary {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }
    .status { min-height: 22px; margin-top: 12px; color: var(--hint); font-size: 14px; }
  </style>
</head>
<body>
  <h1>👤 Мои данные</h1>
  <p>Сохраните свои данные и данные партнёра. Потом бот сможет подтягивать их в разбор, вместо этой вечной человеческой радости «введите всё заново».</p>

  <div class="card">
    <div class="title">Ваши данные</div>
    <label for="self_name">Имя</label>
    <input id="self_name" autocomplete="name" placeholder="Например: Анна" />
    <label for="self_birth_date">Дата рождения</label>
    <input id="self_birth_date" inputmode="numeric" placeholder="12.04.1993" />
  </div>

  <div class="card">
    <div class="title">Партнёр</div>
    <label for="partner_name">Имя партнёра</label>
    <input id="partner_name" placeholder="Например: Андрей" />
    <label for="partner_birth_date">Дата рождения партнёра</label>
    <input id="partner_birth_date" inputmode="numeric" placeholder="06.11.1995" />
  </div>

  <button id="save">Сохранить</button>
  <button id="close" class="secondary">Закрыть</button>
  <div class="status" id="status"></div>

  <script>
    const tg = window.Telegram && window.Telegram.WebApp;
    const statusEl = document.getElementById('status');
    const fields = ['self_name', 'self_birth_date', 'partner_name', 'partner_birth_date'];

    function status(text) { statusEl.textContent = text || ''; }
    function profileFromForm() {
      const result = {};
      for (const id of fields) result[id] = document.getElementById(id).value.trim();
      return result;
    }
    function fillForm(profile) {
      for (const id of fields) document.getElementById(id).value = profile[id] || '';
    }
    async function api(action, profile) {
      const response = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, profile, initData: tg ? tg.initData : '' })
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Ошибка запроса');
      return data;
    }

    async function load() {
      if (!tg || !tg.initData) {
        status('Откройте это окно из Telegram, иначе идентификация не сработает. Да, безопасность решила вмешаться.');
        return;
      }
      tg.ready();
      tg.expand();
      status('Загружаю данные…');
      try {
        const data = await api('get');
        fillForm(data.profile || {});
        status('Данные загружены.');
      } catch (error) {
        status(error.message);
      }
    }

    document.getElementById('save').addEventListener('click', async () => {
      status('Сохраняю…');
      try {
        const data = await api('save', profileFromForm());
        fillForm(data.profile || {});
        status('Сохранено. Теперь бот сможет подтянуть эти данные.');
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      } catch (error) {
        status(error.message);
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
      }
    });
    document.getElementById('close').addEventListener('click', () => {
      if (tg) tg.close();
    });

    load();
  </script>
</body>
</html>
"""


class WebAppHandler(BaseHTTPRequestHandler):
    server_version = "PartnerKeyWebApp/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("WEBAPP: " + format, *args)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/healthz":
            self._send_json({"ok": True})
            return
        if path == "/webapp":
            self._send_html(WEBAPP_HTML)
            return
        self._send_json({"ok": False, "error": "not_found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/api/profile":
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        try:
            payload = self._read_json()
            user_id = _validate_init_data(str(payload.get("initData", "")))
            action = str(payload.get("action", "get"))
            store = get_store()
            if action == "save":
                profile = store.save_profile(
                    user_id,
                    payload.get("profile") if isinstance(payload.get("profile"), dict) else {},
                )
            else:
                profile = store.get_profile(user_id)
            self._send_json({"ok": True, "profile": profile})
        except Exception as exc:
            logger.warning("WEBAPP_PROFILE_ERROR: %s", exc)
            self._send_json({"ok": False, "error": str(exc)}, status=400)


def start_webapp_server() -> ThreadingHTTPServer:
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), WebAppHandler)
    thread = threading.Thread(target=server.serve_forever, name="telegram-webapp-server", daemon=True)
    thread.start()
    logger.info("WEBAPP_SERVER: started on port %s", port)
    return server
