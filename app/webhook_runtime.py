from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import threading
from http.server import ThreadingHTTPServer
from urllib.parse import urlparse

from telegram import Update
from telegram.ext import Application

from app import webapp
from app.config import settings

logger = logging.getLogger(__name__)

_application: Application | None = None
_application_loop: asyncio.AbstractEventLoop | None = None
_ready = threading.Event()
_webhook_secret = ""


def _public_webhook_url() -> str:
    explicit = (os.getenv("TELEGRAM_WEBHOOK_URL") or "").strip()
    if explicit:
        return explicit.rstrip("/")

    parsed = urlparse(settings.webapp_url)
    if not parsed.scheme or not parsed.netloc:
        raise RuntimeError("WEBAPP_URL must be a public absolute URL for Telegram webhook mode")
    return f"{parsed.scheme}://{parsed.netloc}/telegram/webhook"


def _secret_token() -> str:
    explicit = (os.getenv("TELEGRAM_WEBHOOK_SECRET") or "").strip()
    if explicit:
        return explicit
    return hashlib.sha256(
        f"partner-key-webhook:{settings.telegram_bot_token}".encode("utf-8")
    ).hexdigest()


def _log_future_error(future) -> None:
    try:
        future.result()
    except Exception:
        logger.exception("TELEGRAM_WEBHOOK_UPDATE_FAILED")


class WebhookWebAppHandler(webapp.WebAppHandler):
    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/telegram/webhook":
            super().do_POST()
            return

        if not _ready.is_set() or _application is None or _application_loop is None:
            self._send_json({"ok": False, "error": "telegram_not_ready"}, status=503)
            return

        supplied_secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if not supplied_secret or supplied_secret != _webhook_secret:
            self._send_json({"ok": False, "error": "forbidden"}, status=403)
            return

        try:
            payload = self._read_json()
            update = Update.de_json(payload, _application.bot)
            if update is None:
                raise ValueError("Telegram update is empty")
            future = asyncio.run_coroutine_threadsafe(
                _application.update_queue.put(update),
                _application_loop,
            )
            future.add_done_callback(_log_future_error)
            self._send_json({"ok": True})
        except Exception as exc:
            logger.exception("TELEGRAM_WEBHOOK_ACCEPT_FAILED")
            self._send_json({"ok": False, "error": str(exc)}, status=400)


def _start_application(application: Application, webhook_url: str, secret: str) -> None:
    global _application_loop

    loop = asyncio.new_event_loop()
    _application_loop = loop
    asyncio.set_event_loop(loop)

    async def boot() -> None:
        await application.initialize()
        if application.post_init is not None:
            await application.post_init(application)
        await application.start()
        await application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=Update.ALL_TYPES,
            secret_token=secret,
            drop_pending_updates=False,
        )
        _ready.set()
        logger.info("TELEGRAM_WEBHOOK_READY: %s", webhook_url)

    try:
        loop.run_until_complete(boot())
        loop.run_forever()
    except Exception:
        logger.exception("TELEGRAM_WEBHOOK_RUNTIME_FAILED")
        raise


def run_webhook_application(application: Application) -> None:
    global _application, _webhook_secret

    settings.validate_runtime()
    _application = application
    _webhook_secret = _secret_token()
    webhook_url = _public_webhook_url()

    telegram_thread = threading.Thread(
        target=_start_application,
        args=(application, webhook_url, _webhook_secret),
        name="telegram-webhook-runtime",
        daemon=True,
    )
    telegram_thread.start()

    if not _ready.wait(timeout=30):
        raise RuntimeError("Telegram webhook runtime did not become ready in 30 seconds")

    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), WebhookWebAppHandler)
    logger.info("WEBHOOK_HTTP_SERVER: listening on 0.0.0.0:%s", port)
    server.serve_forever()
