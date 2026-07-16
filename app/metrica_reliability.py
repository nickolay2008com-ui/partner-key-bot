from __future__ import annotations

import json
import logging
import threading
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

from app import ad_attribution
import app.webapp as webapp

logger = logging.getLogger(__name__)

STATUS_URL = (
    "https://api-metrika.yandex.net/management/v1/counter/"
    "{counter_id}/offline_conversions/uploading/{upload_id}"
)
LIST_URL = (
    "https://api-metrika.yandex.net/management/v1/counter/"
    "{counter_id}/offline_conversions/uploadings?limit=1&type=BASIC"
)
FINAL_SUCCESS = {"PROCESSED"}
FINAL_FAILURE = {"LINKAGE_FAILURE"}
_FLUSH_LOCK = threading.Lock()
_INSTALLED = False


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _safe_int(value: object) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _ensure_schema(store: ad_attribution.AttributionStore) -> None:
    if store.database_url:
        with store._postgres() as conn:
            conn.execute(
                "ALTER TABLE metrica_offline_queue "
                "ADD COLUMN IF NOT EXISTS remote_status TEXT NOT NULL DEFAULT ''"
            )
            conn.execute(
                "ALTER TABLE metrica_offline_queue "
                "ADD COLUMN IF NOT EXISTS checked_at TEXT"
            )
        return

    with store._sqlite() as conn:
        columns = {
            str(row["name"])
            for row in conn.execute("PRAGMA table_info(metrica_offline_queue)").fetchall()
        }
        if "remote_status" not in columns:
            conn.execute(
                "ALTER TABLE metrica_offline_queue "
                "ADD COLUMN remote_status TEXT NOT NULL DEFAULT ''"
            )
        if "checked_at" not in columns:
            conn.execute("ALTER TABLE metrica_offline_queue ADD COLUMN checked_at TEXT")


def _uploaded_rows(
    store: ad_attribution.AttributionStore,
    limit: int = 25,
) -> list[dict[str, Any]]:
    if store.database_url:
        with store._postgres() as conn:
            rows = conn.execute(
                """
                SELECT * FROM metrica_offline_queue
                WHERE status = 'uploaded' AND upload_id <> ''
                ORDER BY id
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
    else:
        with store._sqlite() as conn:
            rows = conn.execute(
                """
                SELECT * FROM metrica_offline_queue
                WHERE status = 'uploaded' AND upload_id <> ''
                ORDER BY id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def _mark_uploaded(
    store: ad_attribution.AttributionStore,
    row_id: int,
    upload_id: str,
) -> None:
    now = _now()
    if store.database_url:
        with store._postgres() as conn:
            conn.execute(
                """
                UPDATE metrica_offline_queue
                SET status = 'uploaded',
                    attempts = attempts + 1,
                    last_error = '',
                    upload_id = %s,
                    remote_status = 'ACCEPTED',
                    checked_at = %s,
                    sent_at = NULL
                WHERE id = %s
                """,
                (upload_id[:160], now, row_id),
            )
        return

    with store._sqlite() as conn:
        conn.execute(
            """
            UPDATE metrica_offline_queue
            SET status = 'uploaded',
                attempts = attempts + 1,
                last_error = '',
                upload_id = ?,
                remote_status = 'ACCEPTED',
                checked_at = ?,
                sent_at = NULL
            WHERE id = ?
            """,
            (upload_id[:160], now, row_id),
        )


def _mark_remote_state(
    store: ad_attribution.AttributionStore,
    row_id: int,
    *,
    status: str,
    source_quantity: int | None = None,
    line_quantity: int | None = None,
) -> None:
    status = status.upper().strip()[:80] or "UNKNOWN"
    now = _now()
    detail = ""
    if source_quantity is not None or line_quantity is not None:
        detail = (
            f"source={source_quantity if source_quantity is not None else '?'};"
            f"validated={line_quantity if line_quantity is not None else '?'}"
        )

    if status in FINAL_SUCCESS:
        local_status = "sent"
        last_error = ""
        sent_at: str | None = now
    elif status in FINAL_FAILURE:
        local_status = "linkage_failure"
        last_error = "Yandex Metrica could not link yclid to a Direct visit"
        sent_at = None
    else:
        local_status = "uploaded"
        last_error = detail
        sent_at = None

    if store.database_url:
        with store._postgres() as conn:
            conn.execute(
                """
                UPDATE metrica_offline_queue
                SET status = %s,
                    remote_status = %s,
                    checked_at = %s,
                    last_error = %s,
                    sent_at = %s
                WHERE id = %s
                """,
                (local_status, status, now, last_error[:500], sent_at, row_id),
            )
        return

    with store._sqlite() as conn:
        conn.execute(
            """
            UPDATE metrica_offline_queue
            SET status = ?,
                remote_status = ?,
                checked_at = ?,
                last_error = ?,
                sent_at = ?
            WHERE id = ?
            """,
            (local_status, status, now, last_error[:500], sent_at, row_id),
        )


def _mark_check_error(
    store: ad_attribution.AttributionStore,
    row_id: int,
    error: str,
) -> None:
    now = _now()
    if store.database_url:
        with store._postgres() as conn:
            conn.execute(
                """
                UPDATE metrica_offline_queue
                SET attempts = attempts + 1,
                    last_error = %s,
                    checked_at = %s
                WHERE id = %s
                """,
                (error[:500], now, row_id),
            )
        return

    with store._sqlite() as conn:
        conn.execute(
            """
            UPDATE metrica_offline_queue
            SET attempts = attempts + 1,
                last_error = ?,
                checked_at = ?
            WHERE id = ?
            """,
            (error[:500], now, row_id),
        )


def _authorized_json(url: str) -> dict[str, Any]:
    token = ad_attribution._oauth_token()
    if not token:
        raise RuntimeError("YANDEX_METRICA_OAUTH_TOKEN is not configured")
    request = Request(
        url,
        method="GET",
        headers={
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
            "User-Agent": "partner-key-bot/1.1",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Metrica HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Metrica network error: {exc.reason}") from exc


def fetch_upload_status(upload_id: str) -> dict[str, Any]:
    counter_id = ad_attribution._counter_id()
    normalized_id = str(upload_id or "").strip()
    if not counter_id:
        raise RuntimeError("YANDEX_METRICA_ID is not configured")
    if not normalized_id.isdigit():
        raise RuntimeError("Invalid Yandex upload id")
    payload = _authorized_json(
        STATUS_URL.format(counter_id=counter_id, upload_id=normalized_id)
    )
    uploading = payload.get("uploading") if isinstance(payload, dict) else None
    if not isinstance(uploading, dict):
        raise RuntimeError("Metrica returned no uploading object")
    return uploading


def probe_metrica_access() -> dict[str, Any]:
    counter_id = ad_attribution._counter_id()
    if not counter_id:
        return {"ok": False, "error": "YANDEX_METRICA_ID is not configured"}
    try:
        payload = _authorized_json(LIST_URL.format(counter_id=counter_id))
    except Exception as exc:
        return {"ok": False, "error": str(exc)[:500]}
    uploadings = payload.get("uploadings") if isinstance(payload, dict) else None
    if not isinstance(uploadings, list):
        return {"ok": False, "error": "Unexpected Metrica response"}
    latest = uploadings[0] if uploadings and isinstance(uploadings[0], dict) else {}
    return {
        "ok": True,
        "latest_upload_status": str(latest.get("status") or ""),
        "latest_upload_id": str(latest.get("id") or ""),
    }


def flush_pending_verified() -> int:
    if (
        not ad_attribution._counter_id()
        or not ad_attribution._oauth_token()
        or not _FLUSH_LOCK.acquire(blocking=False)
    ):
        return 0

    completed = 0
    try:
        store = ad_attribution.get_store()
        _ensure_schema(store)

        for row in store.pending():
            try:
                upload_id = ad_attribution.upload_conversion(row)
                if not upload_id or not str(upload_id).isdigit():
                    raise RuntimeError("Metrica accepted the file but returned no upload id")
                _mark_uploaded(store, int(row["id"]), str(upload_id))
            except Exception as exc:
                store.mark_failed(int(row["id"]), str(exc))
                logger.warning(
                    "YANDEX_OFFLINE_UPLOAD_FAILED: id=%s error=%s",
                    row.get("id"),
                    exc,
                )

        for row in _uploaded_rows(store):
            try:
                remote = fetch_upload_status(str(row.get("upload_id") or ""))
                status = str(remote.get("status") or "").upper()
                _mark_remote_state(
                    store,
                    int(row["id"]),
                    status=status,
                    source_quantity=_safe_int(remote.get("source_quantity")),
                    line_quantity=_safe_int(remote.get("line_quantity")),
                )
                if status in FINAL_SUCCESS:
                    completed += 1
                elif status in FINAL_FAILURE:
                    logger.error(
                        "YANDEX_OFFLINE_LINKAGE_FAILURE: id=%s upload_id=%s target=%s",
                        row.get("id"),
                        row.get("upload_id"),
                        row.get("target"),
                    )
            except Exception as exc:
                _mark_check_error(store, int(row["id"]), str(exc))
                logger.warning(
                    "YANDEX_OFFLINE_STATUS_FAILED: id=%s upload_id=%s error=%s",
                    row.get("id"),
                    row.get("upload_id"),
                    exc,
                )
    finally:
        _FLUSH_LOCK.release()
    return completed


def _queue_summary(store: ad_attribution.AttributionStore) -> dict[str, Any]:
    _ensure_schema(store)
    if store.database_url:
        with store._postgres() as conn:
            counts = conn.execute(
                """
                SELECT status, COUNT(*) AS quantity
                FROM metrica_offline_queue
                GROUP BY status
                ORDER BY status
                """
            ).fetchall()
            latest = conn.execute(
                """
                SELECT status, remote_status, checked_at, last_error
                FROM metrica_offline_queue
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()
    else:
        with store._sqlite() as conn:
            counts = conn.execute(
                """
                SELECT status, COUNT(*) AS quantity
                FROM metrica_offline_queue
                GROUP BY status
                ORDER BY status
                """
            ).fetchall()
            latest = conn.execute(
                """
                SELECT status, remote_status, checked_at, last_error
                FROM metrica_offline_queue
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()

    latest_data = dict(latest) if latest is not None else {}
    return {
        "counts": {str(row["status"]): int(row["quantity"]) for row in counts},
        "latest": {
            "status": str(latest_data.get("status") or ""),
            "remote_status": str(latest_data.get("remote_status") or ""),
            "checked_at": str(latest_data.get("checked_at") or ""),
            "last_error": str(latest_data.get("last_error") or "")[:300],
        },
    }


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    store = ad_attribution.get_store()
    _ensure_schema(store)
    ad_attribution.flush_pending = flush_pending_verified

    original_get = webapp.WebAppHandler.do_GET

    def do_get_with_analytics_health(self: webapp.WebAppHandler) -> None:
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/") or "/"
        if path != "/healthz/analytics":
            original_get(self)
            return

        query = parse_qs(parsed.query, keep_blank_values=True)
        probe = ((query.get("probe") or [""])[0]).strip() in {"1", "true", "yes"}
        payload: dict[str, Any] = {
            "ok": bool(
                ad_attribution._counter_id()
                and ad_attribution._oauth_token()
                and ad_attribution._bot_username()
            ),
            "configuration": {
                "counter_id": ad_attribution._counter_id(),
                "oauth_configured": bool(ad_attribution._oauth_token()),
                "bot_username_configured": bool(ad_attribution._bot_username()),
            },
            "queue": _queue_summary(store),
        }
        if probe:
            payload["metrica_api"] = probe_metrica_access()
            payload["ok"] = bool(payload["ok"] and payload["metrica_api"].get("ok"))
        self._send_json(payload, status=200 if payload["ok"] else 503)

    webapp.WebAppHandler.do_GET = do_get_with_analytics_health
    _INSTALLED = True
    logger.info("YANDEX_RELIABILITY: upload status verification and health endpoint enabled")
