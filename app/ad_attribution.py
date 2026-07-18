from __future__ import annotations

import asyncio
import csv
import html
import io
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlparse
from urllib.request import Request, urlopen

import psycopg
from psycopg.rows import dict_row

import app.webapp as webapp
from app.config import settings
from app.metrica_layer import _client_script

logger = logging.getLogger(__name__)

ATTRIBUTION_PREFIX = "ad_"
ATTRIBUTION_TTL_DAYS = 21
RETRY_INTERVAL_SECONDS = 60
LANDING_PATH_VARIANTS = {
    "/go/money": "money",
    "/go/message": "message",
    "/go/after-conflict": "after_conflict",
    "/go/care": "care",
    "/go/mistake": "mistake",
    "/go/contribution": "contribution",
    "/go/growth": "growth",
    "/go/instruction": "instruction",
    "/go/instruction-care": "instruction_care",
    "/go/instruction-growth": "instruction_growth",
    "/go/instruction-today": "instruction_today",
}
LANDING_VARIANTS = {"relationship", *LANDING_PATH_VARIANTS.values()}
UPLOAD_URL = "https://api-metrika.yandex.net/management/v1/counter/{counter_id}/offline_conversions/upload"

EVENT_TARGETS = {
    "man_free_report_generated": "free_key_received",
    "couple_bridge_generated": "bridge_received",
    "premium_gate_hit": "paywall_viewed",
    "premium_paywall_viewed": "paywall_viewed",
    "premium_yookassa_payment_started": "payment_started",
    "premium_invoice_opened": "payment_started",
    "premium_payment_succeeded": "purchase_success",
}

_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{6,48}$")
_YCLID_RE = re.compile(r"^[A-Za-z0-9._~-]{1,512}$")
_SEND_LOCK = threading.Lock()
_STORE: AttributionStore | None = None
_INSTALLED = False


class AttributionStore:
    def __init__(self, db_path: Path, database_url: str | None = None) -> None:
        self.db_path = db_path
        self.database_url = database_url.strip() if database_url else None
        if self.database_url:
            self._init_postgres()
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()

    def _sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _postgres(self) -> psycopg.Connection[dict[str, Any]]:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init_sqlite(self) -> None:
        with self._sqlite() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS ad_attributions (
                    token TEXT PRIMARY KEY,
                    yclid TEXT NOT NULL,
                    utm_source TEXT NOT NULL DEFAULT '',
                    utm_medium TEXT NOT NULL DEFAULT '',
                    utm_campaign TEXT NOT NULL DEFAULT '',
                    utm_content TEXT NOT NULL DEFAULT '',
                    utm_term TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    user_id INTEGER,
                    bound_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ad_attributions_user_id
                    ON ad_attributions(user_id);

                CREATE TABLE IF NOT EXISTS metrica_offline_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_key TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    yclid TEXT NOT NULL,
                    target TEXT NOT NULL,
                    event_time INTEGER NOT NULL,
                    price REAL,
                    currency TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    upload_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_metrica_offline_queue_status
                    ON metrica_offline_queue(status, id);
                """
            )

    def _init_postgres(self) -> None:
        with self._postgres() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS ad_attributions (
                    token TEXT PRIMARY KEY,
                    yclid TEXT NOT NULL,
                    utm_source TEXT NOT NULL DEFAULT '',
                    utm_medium TEXT NOT NULL DEFAULT '',
                    utm_campaign TEXT NOT NULL DEFAULT '',
                    utm_content TEXT NOT NULL DEFAULT '',
                    utm_term TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    user_id BIGINT,
                    bound_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ad_attributions_user_id ON ad_attributions(user_id)")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS metrica_offline_queue (
                    id BIGINT GENERATED BY DEFAULT AS IDENTITY PRIMARY KEY,
                    event_key TEXT NOT NULL UNIQUE,
                    user_id BIGINT NOT NULL,
                    yclid TEXT NOT NULL,
                    target TEXT NOT NULL,
                    event_time BIGINT NOT NULL,
                    price DOUBLE PRECISION,
                    currency TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempts INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT NOT NULL DEFAULT '',
                    upload_id TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    sent_at TEXT
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrica_offline_queue_status "
                "ON metrica_offline_queue(status, id)"
            )

    def create_click(self, yclid: str, utm: dict[str, str]) -> str:
        token = secrets.token_urlsafe(12)[:20]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        values = (
            token,
            yclid,
            utm.get("utm_source", "")[:160],
            utm.get("utm_medium", "")[:160],
            utm.get("utm_campaign", "")[:160],
            utm.get("utm_content", "")[:160],
            utm.get("utm_term", "")[:160],
            now,
        )
        if self.database_url:
            with self._postgres() as conn:
                conn.execute(
                    """
                    INSERT INTO ad_attributions (
                        token, yclid, utm_source, utm_medium, utm_campaign,
                        utm_content, utm_term, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values,
                )
        else:
            with self._sqlite() as conn:
                conn.execute(
                    """
                    INSERT INTO ad_attributions (
                        token, yclid, utm_source, utm_medium, utm_campaign,
                        utm_content, utm_term, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
        return token

    def bind(self, token: str, user_id: int) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.database_url:
            with self._postgres() as conn:
                row = conn.execute("SELECT * FROM ad_attributions WHERE token = %s", (token,)).fetchone()
                if row is None or (row.get("user_id") not in {None, user_id}):
                    return None
                conn.execute(
                    "UPDATE ad_attributions SET user_id = %s, bound_at = %s WHERE token = %s",
                    (user_id, now, token),
                )
        else:
            with self._sqlite() as conn:
                row = conn.execute("SELECT * FROM ad_attributions WHERE token = ?", (token,)).fetchone()
                if row is None or (row["user_id"] not in {None, user_id}):
                    return None
                conn.execute(
                    "UPDATE ad_attributions SET user_id = ?, bound_at = ? WHERE token = ?",
                    (user_id, now, token),
                )
        return dict(row)

    def by_token(self, token: str) -> dict[str, Any] | None:
        if self.database_url:
            with self._postgres() as conn:
                row = conn.execute("SELECT * FROM ad_attributions WHERE token = %s", (token,)).fetchone()
        else:
            with self._sqlite() as conn:
                row = conn.execute("SELECT * FROM ad_attributions WHERE token = ?", (token,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        try:
            created_at = datetime.fromisoformat(str(result["created_at"]))
        except (TypeError, ValueError):
            return None
        if datetime.now(timezone.utc) - created_at > timedelta(days=ATTRIBUTION_TTL_DAYS):
            return None
        return result

    def latest_for_user(self, user_id: int) -> dict[str, Any] | None:
        query = (
            "SELECT * FROM ad_attributions WHERE user_id = {placeholder} "
            "ORDER BY COALESCE(bound_at, created_at) DESC LIMIT 1"
        )
        if self.database_url:
            with self._postgres() as conn:
                row = conn.execute(query.format(placeholder="%s"), (user_id,)).fetchone()
        else:
            with self._sqlite() as conn:
                row = conn.execute(query.format(placeholder="?"), (user_id,)).fetchone()
        if row is None:
            return None
        result = dict(row)
        try:
            created_at = datetime.fromisoformat(str(result["created_at"]))
        except (TypeError, ValueError):
            return None
        if datetime.now(timezone.utc) - created_at > timedelta(days=ATTRIBUTION_TTL_DAYS):
            return None
        return result

    def enqueue(
        self,
        *,
        event_key: str,
        user_id: int,
        yclid: str,
        target: str,
        event_time: int,
        price: float | None,
        currency: str | None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        values = (event_key, user_id, yclid, target, event_time, price, currency, now)
        if self.database_url:
            with self._postgres() as conn:
                cursor = conn.execute(
                    """
                    INSERT INTO metrica_offline_queue (
                        event_key, user_id, yclid, target, event_time, price, currency, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(event_key) DO NOTHING
                    """,
                    values,
                )
                return cursor.rowcount > 0
        with self._sqlite() as conn:
            cursor = conn.execute(
                """
                INSERT OR IGNORE INTO metrica_offline_queue (
                    event_key, user_id, yclid, target, event_time, price, currency, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            return cursor.rowcount > 0

    def pending(self, limit: int = 25) -> list[dict[str, Any]]:
        if self.database_url:
            with self._postgres() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM metrica_offline_queue
                    WHERE status IN ('pending', 'failed') AND attempts < 20
                    ORDER BY id LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
        else:
            with self._sqlite() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM metrica_offline_queue
                    WHERE status IN ('pending', 'failed') AND attempts < 20
                    ORDER BY id LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def mark_sent(self, row_id: int, upload_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.database_url:
            with self._postgres() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'sent', attempts = attempts + 1, last_error = '',
                        upload_id = %s, sent_at = %s
                    WHERE id = %s
                    """,
                    (upload_id[:160], now, row_id),
                )
        else:
            with self._sqlite() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'sent', attempts = attempts + 1, last_error = '',
                        upload_id = ?, sent_at = ?
                    WHERE id = ?
                    """,
                    (upload_id[:160], now, row_id),
                )

    def mark_failed(self, row_id: int, error: str) -> None:
        if self.database_url:
            with self._postgres() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'failed', attempts = attempts + 1, last_error = %s
                    WHERE id = %s
                    """,
                    (error[:500], row_id),
                )
        else:
            with self._sqlite() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'failed', attempts = attempts + 1, last_error = ?
                    WHERE id = ?
                    """,
                    (error[:500], row_id),
                )


def get_store() -> AttributionStore:
    global _STORE
    if _STORE is None:
        _STORE = AttributionStore(settings.reports_db_path(), settings.database_url)
    return _STORE


def _counter_id() -> int | None:
    try:
        value = int(os.getenv("YANDEX_METRICA_ID", "").strip())
    except ValueError:
        return None
    return value if value > 0 else None


def _oauth_token() -> str:
    return os.getenv("YANDEX_METRICA_OAUTH_TOKEN", "").strip()


def _bot_username() -> str:
    return (os.getenv("TELEGRAM_BOT_USERNAME") or os.getenv("BOT_USERNAME") or "").strip().lstrip("@")


def _query_value(query: dict[str, list[str]], key: str) -> str:
    return ((query.get(key) or [""])[0]).strip()[:512]


def _is_landing_path(raw_path: str) -> bool:
    path = urlparse(raw_path).path.rstrip("/") or "/"
    return path in {"/", "/go", *LANDING_PATH_VARIANTS}


def build_landing_html(
    bot_link: str,
    attributed: bool,
    token: str = "",
    variant: str = "relationship",
) -> str:
    note = (
        "Рекламный переход сохранён. Дальше бот свяжет действия и оплату с объявлением."
        if attributed
        else "Открываем бот. Для рекламной атрибуции в адресе должен быть параметр yclid."
    )
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Открываем Астро Партнёра</title>
  {_client_script()}
  <style>
    :root {{ color-scheme: light dark; --bg:#100f17; --card:#1d1928; --text:#f8fafc; --muted:#b7afc7; --button:#8b5cf6; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:24px; background:radial-gradient(circle at top,#3b2852,var(--bg) 48%); color:var(--text); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(520px,100%); padding:28px; border-radius:28px; background:rgba(29,25,40,.95); border:1px solid rgba(255,255,255,.12); text-align:center; }}
    h1 {{ margin:8px 0 12px; font-size:28px; }}
    p {{ margin:0 0 20px; color:var(--muted); line-height:1.5; }}
    a {{ display:block; padding:15px 18px; border-radius:16px; background:var(--button); color:white; font-weight:800; text-decoration:none; }}
    small {{ display:block; margin-top:14px; color:var(--muted); }}
  </style>
</head>
<body>
  <main>
    <div style="font-size:42px">💞</div>
    <h1>Открываем инструкцию к вашему мужчине</h1>
    <p>{html.escape(note)}</p>
    <a id="open-bot" href="{html.escape(bot_link, quote=True)}">Открыть Telegram-бот</a>
    <small>Если Telegram не открылся автоматически, нажмите кнопку.</small>
  </main>
  <script>
    const target = {json.dumps(bot_link)};
    let redirected = false;
    function openBot() {{
      if (redirected) return;
      redirected = true;
      if (window.partnerMetricsTrack) window.partnerMetricsTrack('landing_to_bot', {{ attributed: {str(attributed).lower()} }});
      setTimeout(() => window.location.href = target, 250);
    }}
    document.getElementById('open-bot').addEventListener('click', (event) => {{ event.preventDefault(); openBot(); }});
    setTimeout(openBot, 1200);
  </script>
</body>
</html>"""


def _render_landing(handler: webapp.WebAppHandler) -> None:
    username = _bot_username()
    if not username:
        handler._send_html("<h1>Не задан TELEGRAM_BOT_USERNAME</h1><p>Добавьте имя бота без @ в Railway.</p>")
        return
    query = parse_qs(urlparse(handler.path).query, keep_blank_values=True)
    path = urlparse(handler.path).path.rstrip("/") or "/"
    variant = LANDING_PATH_VARIANTS.get(path, "relationship")
    yclid = _query_value(query, "yclid")
    token = ""
    if yclid and _YCLID_RE.fullmatch(yclid):
        token = get_store().create_click(
            yclid,
            {key: _query_value(query, key) for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")},
        )
    bot_link = f"https://t.me/{quote(username, safe='')}"
    if token:
        bot_link += "?" + urlencode({"start": f"{ATTRIBUTION_PREFIX}{token}"})
    handler._send_html(build_landing_html(bot_link, bool(token), token, variant))


def _record_landing_click(token: str, variant: str = "relationship") -> bool:
    if not _TOKEN_RE.fullmatch(token):
        return False
    attribution = get_store().by_token(token)
    if not attribution:
        return False
    variant = variant if variant in LANDING_VARIANTS else "relationship"
    inserted = get_store().enqueue(
        event_key=f"landing_to_bot:{variant}:{token}",
        user_id=0,
        yclid=str(attribution["yclid"]),
        target="landing_to_bot",
        event_time=int(time.time()),
        price=None,
        currency=None,
    )
    if inserted:
        threading.Thread(target=flush_pending, name="metrica-landing-flush", daemon=True).start()
    return inserted


def _render_landing_out(handler: webapp.WebAppHandler) -> None:
    username = _bot_username()
    if not username:
        handler._send_body(
            b"<h1>TELEGRAM_BOT_USERNAME is not configured</h1>",
            content_type="text/html; charset=utf-8",
            status=503,
        )
        return
    query = parse_qs(urlparse(handler.path).query, keep_blank_values=True)
    token = _query_value(query, "token")
    variant = _query_value(query, "variant")
    variant = variant if variant in LANDING_VARIANTS else "relationship"
    if _TOKEN_RE.fullmatch(token):
        _record_landing_click(token, variant)
    bot_link = f"https://t.me/{quote(username, safe='')}"
    if _TOKEN_RE.fullmatch(token):
        bot_link += "?" + urlencode({"start": f"{ATTRIBUTION_PREFIX}{token}"})
    handler.send_response(302)
    handler.send_header("Location", bot_link)
    handler.send_header("Cache-Control", "no-store")
    handler.send_header("Content-Length", "0")
    handler.end_headers()


def conversion_csv(row: dict[str, Any]) -> bytes:
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(["Yclid", "Target", "DateTime", "Price", "Currency"])
    writer.writerow(
        [
            row["yclid"],
            row["target"],
            int(row["event_time"]),
            "" if row.get("price") is None else f"{float(row['price']):.2f}",
            row.get("currency") or "",
        ]
    )
    return stream.getvalue().encode("utf-8")


def _multipart(csv_bytes: bytes) -> tuple[bytes, str]:
    boundary = "----PartnerKey" + secrets.token_hex(12)
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            b'Content-Disposition: form-data; name="file"; filename="conversions.csv"\r\n',
            b"Content-Type: text/csv; charset=utf-8\r\n\r\n",
            csv_bytes,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return body, boundary


def upload_conversion(row: dict[str, Any]) -> str:
    counter_id = _counter_id()
    oauth_token = _oauth_token()
    if not counter_id or not oauth_token:
        raise RuntimeError("YANDEX_METRICA_ID or YANDEX_METRICA_OAUTH_TOKEN is not configured")
    body, boundary = _multipart(conversion_csv(row))
    url = UPLOAD_URL.format(counter_id=counter_id) + "?" + urlencode({"client_id_type": "YCLID"})
    request = Request(
        url,
        data=body,
        method="POST",
        headers={
            "Authorization": f"OAuth {oauth_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "partner-key-bot/1.0",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Metrica HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Metrica network error: {exc.reason}") from exc
    uploading = payload.get("uploading") if isinstance(payload, dict) else None
    if isinstance(uploading, dict):
        return str(uploading.get("id") or uploading.get("upload_id") or "")
    return str(payload.get("id") or "") if isinstance(payload, dict) else ""


def flush_pending() -> int:
    if not _counter_id() or not _oauth_token() or not _SEND_LOCK.acquire(blocking=False):
        return 0
    sent = 0
    try:
        store = get_store()
        for row in store.pending():
            try:
                store.mark_sent(int(row["id"]), upload_conversion(row))
                sent += 1
            except Exception as exc:
                store.mark_failed(int(row["id"]), str(exc))
                logger.warning("YANDEX_OFFLINE_CONVERSION_FAILED: id=%s error=%s", row.get("id"), exc)
    finally:
        _SEND_LOCK.release()
    return sent


def enqueue_conversion(
    base: Any,
    *,
    user_id: int,
    target: str,
    properties: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
) -> bool:
    attribution = attribution or get_store().latest_for_user(user_id)
    if not attribution:
        return False
    yclid = str(attribution.get("yclid") or "")
    token = str(attribution.get("token") or "")
    if not yclid or not token:
        return False
    properties = properties or {}
    product_key = str(properties.get("product_key") or "")
    report_id = str(properties.get("report_id") or "")
    event_key = f"{target}:{user_id}:{token}"
    if target in {"payment_started", "purchase_success"}:
        event_key += f":{report_id}:{product_key}"
    price: float | None = None
    currency: str | None = None
    if target in {"payment_started", "purchase_success"} and product_key:
        product = base.get_product(product_key)
        if product is not None:
            price = float(product.rubles)
            currency = "RUB"
    inserted = get_store().enqueue(
        event_key=event_key,
        user_id=user_id,
        yclid=yclid,
        target=target,
        event_time=int(time.time()),
        price=price,
        currency=currency,
    )
    if inserted:
        threading.Thread(target=flush_pending, name="metrica-offline-flush", daemon=True).start()
    return inserted


async def _retry_worker() -> None:
    while True:
        try:
            await asyncio.to_thread(flush_pending)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("YANDEX_OFFLINE_RETRY_FAILED")
        await asyncio.sleep(RETRY_INTERVAL_SECONDS)


def install(base: Any) -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original_get = webapp.WebAppHandler.do_GET
    original_track_event = base._track_event
    original_start = base.start
    original_post_init = base._post_init

    def do_get_with_landing(self: webapp.WebAppHandler) -> None:
        if urlparse(self.path).path.rstrip("/") == "/go/out":
            _render_landing_out(self)
            return
        if _is_landing_path(self.path):
            _render_landing(self)
            return
        original_get(self)

    async def track_event_with_offline(update: Any, event_name: str, **properties: Any) -> None:
        await original_track_event(update, event_name, **properties)
        target = EVENT_TARGETS.get(event_name)
        user_id = base._user_id(update)
        if target and user_id is not None:
            await asyncio.to_thread(
                enqueue_conversion,
                base,
                user_id=user_id,
                target=target,
                properties=properties,
            )

    async def start_with_attribution(update: Any, context: Any) -> int:
        args = list(getattr(context, "args", None) or [])
        payload = str(args[0]) if args else ""
        user_id = base._user_id(update)
        if user_id is not None and payload.startswith(ATTRIBUTION_PREFIX):
            token = payload[len(ATTRIBUTION_PREFIX) :]
            if _TOKEN_RE.fullmatch(token):
                attribution = await asyncio.to_thread(get_store().bind, token, user_id)
                if attribution:
                    await asyncio.to_thread(
                        enqueue_conversion,
                        base,
                        user_id=user_id,
                        target="bot_started",
                        attribution=attribution,
                    )
                    await original_track_event(
                        update,
                        "ad_attribution_bound",
                        source="yandex_direct",
                        utm_campaign=str(attribution.get("utm_campaign") or ""),
                        utm_content=str(attribution.get("utm_content") or ""),
                    )
        return await original_start(update, context)

    async def post_init_with_retry(application: Any) -> None:
        await original_post_init(application)
        application.create_task(_retry_worker(), name="yandex-offline-conversion-retry")

    webapp.WebAppHandler.do_GET = do_get_with_landing
    base._track_event = track_event_with_offline
    base.start = start_with_attribution
    base._post_init = post_init_with_retry
    _INSTALLED = True
    logger.info(
        "YANDEX_ATTRIBUTION: landing=/go counter=%s oauth=%s bot=%s",
        _counter_id() or "disabled",
        "configured" if _oauth_token() else "missing",
        _bot_username() or "missing",
    )
