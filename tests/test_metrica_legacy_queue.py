from __future__ import annotations

from pathlib import Path

from app import ad_attribution, metrica_legacy_queue, metrica_reliability


def test_legacy_sent_upload_is_rechecked(tmp_path: Path) -> None:
    store = ad_attribution.AttributionStore(tmp_path / "metrica.sqlite3")
    inserted = store.enqueue(
        event_key="legacy:1",
        user_id=1,
        yclid="yclid-legacy",
        target="bridge_received",
        event_time=1_700_000_000,
        price=None,
        currency=None,
    )
    assert inserted is True
    row = store.pending()[0]
    metrica_reliability._ensure_schema(store)

    with store._sqlite() as conn:
        conn.execute(
            """
            UPDATE metrica_offline_queue
            SET status = 'sent', upload_id = '123', remote_status = ''
            WHERE id = ?
            """,
            (int(row["id"]),),
        )

    rows = metrica_legacy_queue.rows_requiring_verification(store)

    assert len(rows) == 1
    assert rows[0]["status"] == "sent"
    assert rows[0]["upload_id"] == "123"


def test_verified_sent_upload_is_not_polled_again(tmp_path: Path) -> None:
    store = ad_attribution.AttributionStore(tmp_path / "metrica.sqlite3")
    inserted = store.enqueue(
        event_key="verified:1",
        user_id=1,
        yclid="yclid-verified",
        target="purchase_success",
        event_time=1_700_000_000,
        price=199,
        currency="RUB",
    )
    assert inserted is True
    row = store.pending()[0]
    metrica_reliability._ensure_schema(store)

    with store._sqlite() as conn:
        conn.execute(
            """
            UPDATE metrica_offline_queue
            SET status = 'sent', upload_id = '124', remote_status = 'PROCESSED'
            WHERE id = ?
            """,
            (int(row["id"]),),
        )

    assert metrica_legacy_queue.rows_requiring_verification(store) == []
