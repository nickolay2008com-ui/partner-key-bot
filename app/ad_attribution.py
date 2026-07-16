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
UPLOAD_URL = "https://api-metrika.yandex.net/management/v1/counter/{counter_id}/offline_conversions/upload"

_EVENT_TARGETS = {
    "man_free_report_generated": "free_key_received",
    "couple_bridge_generated": "bridge_received",
    "premium_gate_hit": "paywall_viewed",
    "premium_paywall_viewed": "paywall_viewed",
    "premium_yookassa_payment_started": "payment_started",
    "premium_invoice_opened": "payment_started",
    "premium_payment_succeeded": "purchase_success",
}

_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{6,48}$")
_SAFE_YCLID_RE = re.compile(r"^[A-Za-z0-9._~-]{1,512}$")
_SEND_LOCK = threading.Lock()
_INSTALLED = False
_STORE: AttributionStore | None = None


class AttributionStore:
    def __init__(self, db_path: Path, database_url: str | None = None) -> None:
        self.db_path = db_path
        self.database_url = database_url.strip() if database_url else None
        if self.database_url:
            self._init_postgres()
        else:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_sqlite()

    def _connect_sqlite(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _connect_postgres(self) -> psycopg.Connection[dict[str, Any]]:
        if not self.database_url:
            raise RuntimeError("DATABASE_URL is not configured")
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def _init_sqlite(self) -> None:
        with self._connect_sqlite() as conn:
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
                    user_id INTEGER,
                    bound_at TEXT
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ad_attributions_user_id ON ad_attributions(user_id)")
            conn.execute(
                """
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
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_metrica_offline_queue_status ON metrica_offline_queue(status, id)"
            )

    def _init_postgres(self) -> None:
        with self._connect_postgres() as conn:
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
                "CREATE INDEX IF NOT EXISTS idx_metrica_offline_queue_status ON metrica_offline_queue(status, id)"
            )

    def create_click(self, yclid: str, params: dict[str, str]) -> str:
        token = secrets.token_urlsafe(12).replace("-", "_")[:20]
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        values = (
            token,
            yclid,
            params.get("utm_source", "")[:160],
            params.get("utm_medium", "")[:160],
            params.get("utm_campaign", "")[:160],
            params.get("utm_content", "")[:160],
            params.get("utm_term", "")[:160],
            now,
        )
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(
                    """
                    INSERT INTO ad_attributions (
                        token, yclid, utm_source, utm_medium, utm_campaign, utm_content, utm_term, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values,
                )
        else:
            with self._connect_sqlite() as conn:
                conn.execute(
                    """
                    INSERT INTO ad_attributions (
                        token, yclid, utm_source, utm_medium, utm_campaign, utm_content, utm_term, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
        return token

    def bind(self, token: str, user_id: int) -> dict[str, Any] | None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    "SELECT * FROM ad_attributions WHERE token = %s",
                    (token,),
                ).fetchone()
                if row is None:
                    return None
                conn.execute(
                    "UPDATE ad_attributions SET user_id = %s, bound_at = %s WHERE token = %s",
                    (user_id, now, token),
                )
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute("SELECT * FROM ad_attributions WHERE token = ?", (token,)).fetchone()
                if row is None:
                    return None
                conn.execute(
                    "UPDATE ad_attributions SET user_id = ?, bound_at = ? WHERE token = ?",
                    (user_id, now, token),
                )
        return dict(row)

    def latest_for_user(self, user_id: int) -> dict[str, Any] | None:
        if self.database_url:
            with self._connect_postgres() as conn:
                row = conn.execute(
                    """
                    SELECT * FROM ad_attributions
                    WHERE user_id = %s
                    ORDER BY COALESCE(bound_at, created_at) DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
        else:
            with self._connect_sqlite() as conn:
                row = conn.execute(
                    """
                    SELECT * FROM ad_attributions
                    WHERE user_id = ?
                    ORDER BY COALESCE(bound_at, created_at) DESC
                    LIMIT 1
                    """,
                    (user_id,),
                ).fetchone()
        if row is None:
            return None
        data = dict(row)
        try:
            created = datetime.fromisoformat(str(data["created_at"]))
        except (TypeError, ValueError):
            return None
        if datetime.now(timezone.utc) - created > timedelta(days=ATTRIBUTION_TTL_DAYS):
            return None
        return data

    def enqueue(
        self,
        *,
        event_key: str,
        user_id: int,
        yclid: str,
        target: str,
        event_time: int,
        price: float | None = None,
        currency: str | None = None,
    ) -> bool:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        values = (event_key, user_id, yclid, target, event_time, price, currency, now)
        if self.database_url:
            with self._connect_postgres() as conn:
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
        with self._connect_sqlite() as conn:
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
            with self._connect_postgres() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM metrica_offline_queue
                    WHERE status IN ('pending', 'failed') AND attempts < 20
                    ORDER BY id
                    LIMIT %s
                    """,
                    (limit,),
                ).fetchall()
        else:
            with self._connect_sqlite() as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM metrica_offline_queue
                    WHERE status IN ('pending', 'failed') AND attempts < 20
                    ORDER BY id
                    LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
        return [dict(row) for row in rows]

    def mark_sent(self, row_id: int, upload_id: str = "") -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'sent', attempts = attempts + 1, last_error = '', upload_id = %s, sent_at = %s
                    WHERE id = %s
                    """,
                    (upload_id[:160], now, row_id),
                )
        else:
            with self._connect_sqlite() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'sent', attempts = attempts + 1, last_error = '', upload_id = ?, sent_at = ?
                    WHERE id = ?
                    """,
                    (upload_id[:160], now, row_id),
                )

    def mark_failed(self, row_id: int, error: str) -> None:
        if self.database_url:
            with self._connect_postgres() as conn:
                conn.execute(
                    """
                    UPDATE metrica_offline_queue
                    SET status = 'failed', attempts = attempts + 1, last_error = %s
                    WHERE id = %s
                    """,
                    (error[:500], row_id),
                )
        else:
            with self._connect_sqlite() as conn:
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
    raw = os.getenv("YANDEX_METRICA_ID", "").strip()
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def _oauth_token() -> str:
    return os.getenv("YANDEX_METRICA_OAUTH_TOKEN", "").strip()


def _bot_username() -> str:
    return (os.getenv("TELEGRAM_BOT_USERNAME") or os.getenv("BOT_USERNAME") or "").strip().lstrip("@")


def _clean_query_value(query: dict[str, list[str]], key: str) -> str:
    value = (query.get(key) or [""])[0].strip()
    return value[:512]


def _landing_html(bot_link: str, has_attribution: bool) -> str:
    safe_link = html.escape(bot_link, quote=True)
    metric_script = _client_script()
    attribution_note = (
        "Рекламный переход сохранён. Дальше бот сможет связать ключевые действия и оплату с объявлением."
        if has_attribution
        else "Переход откроет бот. Для рекламной атрибуции Яндекс должен добавить параметр yclid."
    )
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Открываем Астро Партнёра</title>
  {metric_script}
  <style>
    :root {{ color-scheme: light dark; --bg:#100f17; --card:#1c1927; --text:#f8fafc; --muted:#b7afc7; --button:#8b5cf6; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:24px; background:radial-gradient(circle at top,#382650,var(--bg) 46%); color:var(--text); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(520px,100%); padding:28px; border-radius:28px; background:rgba(28,25,39,.94); border:1px solid rgba(255,255,255,.12); text-align:center; box-shadow:0 24px 70px rgba(0,0,0,.28); }}
    h1 {{ margin:0 0 12px; font-size:28px; }}
    p {{ margin:0 0 20px; color:var(--muted); line-height:1.5; }}
    a {{ display:block; padding:15px 18px; border-radius:16px; background:var(--button); color:white; font-weight:800; text-decoration:none; }}
    small {{ display:block; margin-top:14px; color:var(--muted); line-height:1.4; }}
  </style>
</head>
<body>
  <main>
    <div style="font-size:42px">💞</div>
    <h1>Открываем инструкцию к вашему мужчине</h1>
    <p>{html.escape(attribution_note)}</p>
    <a id="open-bot" href="{safe_link}">Открыть Telegram-бот</a>
    <small>Если Telegram не открылся автоматически, нажмите кнопку.</small>
  </main>
  <script>
    const target = {json.dumps(bot_link)};
    let redirected = false;
    function openBot() {{
      if (redirected) return;
      redirected = true;
      if (window.partnerMetricsTrack) window.partnerMetricsTrack('landing_to_bot', {{ attributed: {str(has_attribution).lower()} }});
      setTimeout(() => window.location.href = target, 220);
    }}
    document.getElementById('open-bot').addEventListener('click', (event) => {{ event.preventDefault(); openBot(); }});
    setTimeout(openBot, 1100);
  </script>
</body>
</html>"""


def _render_landing(handler: webapp.WebAppHandler) -> None:
    username = _bot_username()
    if not username:
        handler._send_html(
            "<h1>Не задан TELEGRAM_BOT_USERNAME</h1><p>Добавьте имя бота без @ в Railway Variables.</p>"
        )
        return
    query = parse_qs(urlparse(handler.path).query, keep_blank_values=True)
    yclid = _clean_query_value(query, "yclid")
    token = ""
    if yclid and _SAFE_YCLID_RE.fullmatch(yclid):
        token = get_store().create_click(
            yclid,
            {
                key: _clean_query_value(query, key)
                for key in ("utm_source", "utm_medium", "utm_campaign", "utm_content", "utm_term")
            },
        )
    payload = f"{ATTRIBUTION_PREFIX}{token}" if token else ""
    bot_link = f"https://t.me/{quote(username, safe='')}"
    if payload:
        bot_link += "?" + urlencode({"start": payload})
    handler._send_html(_landing_html(bot_link, bool(token)))


def _multipart_csv(csv_bytes: bytes) -> tuple[bytes, str]:
    boundary = "----PartnerKey" + secrets.token_hex(12)
    chunks = [
        f"--{boundary}\r\n".encode(),
        b'Content-Disposition: form-data; name="file"; filename="conversions.csv"\r\n',
        b"Content-Type: text/csv; charset=utf-8\r\n\r\n",
        csv_bytes,
        b"\r\n",
        f"--{boundary}--\r\n".encode(),
    ]
    return b"".join(chunks), boundary


def _csv_for_row(row: dict[str, Any]) -> bytes:
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


def _upload_row(row: dict[str, Any]) -> str:
    counter_id = _counter_id()
    oauth_token = _oauth_token()
    if not counter_id or not oauth_token:
        raise RuntimeError("YANDEX_METRICA_ID or YANDEX_METRICA_OAUTH_TOKEN is not configured")
    body, boundary = _multipart_csv(_csv_for_row(row))
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
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Metrica HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Metrica network error: {exc.reason}") from exc
    upload = payload.get("uploading") if isinstance(payload, dict) else None
    if isinstance(upload, dict):
        return str(upload.get("id") or upload.get("upload_id") or "")
    return str(payload.get("id") or "") if isinstance(payload, dict) else ""


def flush_pending() -> int:
    if not _counter_id() or not _oauth_token():
        return 0
    if not _SEND_LOCK.acquire(blocking=False):
        return 0
    sent = 0
    try:
        store = get_store()
        for row in store.pending():
            try:
                upload_id = _upload_row(row)
                store.mark_sent(int(row["id"]), upload_id)
                sent += 1
            except Exception as exc:
                store.mark_failed(int(row["id"]), str(exc))
                logger.warning("YANDEX_OFFLINE_CONVERSION_FAILED: id=%s error=%s", row.get("id"), exc)
    finally:
        _SEND_LOCK.release()
    return sent


def _enqueue_for_user(
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
    yclid = str(attribution.get("yclid") or "").strip()
    token = str(attribution.get("token") or "").strip()
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

    def do_get_with_attribution(self: webapp.WebAppHandler) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/go":
            _render_landing(self)
            return
        original_get(self)

    async def track_event_with_offline(update: Any, event_name: str, **properties: Any) -> None:
        await original_track_event(update, event_name, **properties)
        target = _EVENT_TARGETS.get(event_name)
        user_id = base._user_id(update)
        if target and user_id is not None:
            await asyncio.to_thread(
                _enqueue_for_user,
                base,
                user_id=user_id,
                target=target,
                properties=properties,
            )

    async def start_with_attribution(update: Any, context: Any) -> int:
        args = list(getattr(context, "args", None) or [])
        payload = str(args[0]) if args else ""
        attribution: dict[str, Any] | None = None
        user_id = base._user_id(update)
        if user_id is not None and payload.startswith(ATTRIBUTION_PREFIX):
            token = payload[len(ATTRIBUTION_PREFIX) :]
            if _SAFE_TOKEN_RE.fullmatch(token):
                attribution = await asyncio.to_thread(get_store().bind, token, user_id)
                if attribution:
                    await asyncio.to_thread(
                        _enqueue_for_user,
                        base,
                        user_id=user_id,
                        target="bot_started",
                        properties={"source": "yandex_direct"},
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

    webapp.WebAppHandler.do_GET = do_get_with_attribution
    base._track_event = track_event_with_offline
    base.start = start_with_attribution
    base._post_init = post_init_with_retry
    _INSTALLED = True
    logger.info(
        "YANDEX_ATTRIBUTION: installed; landing=/go counter=%s oauth=%s bot=%s",
        _counter_id() or "disabled",
        "configured" if _oauth_token() else "missing",
        _bot_username() or "missing",
    )
