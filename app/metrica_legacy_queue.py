from __future__ import annotations

from typing import Any

from app import ad_attribution, metrica_reliability

_INSTALLED = False


def rows_requiring_verification(
    store: ad_attribution.AttributionStore,
    limit: int = 25,
) -> list[dict[str, Any]]:
    condition = """
        upload_id <> ''
        AND (
            status = 'uploaded'
            OR (status = 'sent' AND COALESCE(remote_status, '') = '')
        )
    """
    if store.database_url:
        with store._postgres() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM metrica_offline_queue
                WHERE {condition}
                ORDER BY id
                LIMIT %s
                """,
                (limit,),
            ).fetchall()
    else:
        with store._sqlite() as conn:
            rows = conn.execute(
                f"""
                SELECT * FROM metrica_offline_queue
                WHERE {condition}
                ORDER BY id
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    metrica_reliability._uploaded_rows = rows_requiring_verification
    _INSTALLED = True
