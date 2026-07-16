from __future__ import annotations

from typing import Any

from app import ad_attribution, metrica_reliability

_INSTALLED = False


def _target_counts(store: ad_attribution.AttributionStore) -> dict[str, int]:
    if store.database_url:
        with store._postgres() as conn:
            rows = conn.execute(
                """
                SELECT target, COUNT(*) AS quantity
                FROM metrica_offline_queue
                GROUP BY target
                ORDER BY target
                """
            ).fetchall()
    else:
        with store._sqlite() as conn:
            rows = conn.execute(
                """
                SELECT target, COUNT(*) AS quantity
                FROM metrica_offline_queue
                GROUP BY target
                ORDER BY target
                """
            ).fetchall()
    return {str(row["target"]): int(row["quantity"]) for row in rows}


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original_summary = metrica_reliability._queue_summary

    def queue_summary_with_targets(store: ad_attribution.AttributionStore) -> dict[str, Any]:
        summary = original_summary(store)
        summary["targets"] = _target_counts(store)
        return summary

    metrica_reliability._queue_summary = queue_summary_with_targets
    _INSTALLED = True
