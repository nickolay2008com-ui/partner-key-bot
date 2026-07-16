from __future__ import annotations

from pathlib import Path

from app import ad_attribution, metrica_reliability, metrica_upload_api


def _queued_store(tmp_path: Path) -> tuple[ad_attribution.AttributionStore, int]:
    store = ad_attribution.AttributionStore(tmp_path / "metrica.sqlite3")
    inserted = store.enqueue(
        event_key="bridge_received:1:token",
        user_id=1,
        yclid="test-yclid",
        target="bridge_received",
        event_time=1_700_000_000,
        price=None,
        currency=None,
    )
    assert inserted is True
    row = store.pending()[0]
    return store, int(row["id"])


def test_upload_is_only_sent_after_yandex_processed(tmp_path: Path) -> None:
    store, row_id = _queued_store(tmp_path)
    metrica_reliability._ensure_schema(store)

    metrica_reliability._mark_uploaded(store, row_id, "42")
    uploaded = metrica_reliability._uploaded_rows(store)
    assert uploaded[0]["status"] == "uploaded"
    assert uploaded[0]["remote_status"] == "ACCEPTED"

    metrica_reliability._mark_remote_state(
        store,
        row_id,
        status="PROCESSED",
        source_quantity=1,
        line_quantity=1,
    )
    summary = metrica_reliability._queue_summary(store)
    assert summary["counts"] == {"sent": 1}
    assert summary["latest"]["remote_status"] == "PROCESSED"
    assert summary["latest"]["last_error"] == ""


def test_linkage_failure_is_terminal_and_visible(tmp_path: Path) -> None:
    store, row_id = _queued_store(tmp_path)
    metrica_reliability._ensure_schema(store)
    metrica_reliability._mark_uploaded(store, row_id, "43")

    metrica_reliability._mark_remote_state(
        store,
        row_id,
        status="LINKAGE_FAILURE",
        source_quantity=1,
        line_quantity=1,
    )
    summary = metrica_reliability._queue_summary(store)
    assert summary["counts"] == {"linkage_failure": 1}
    assert summary["latest"]["remote_status"] == "LINKAGE_FAILURE"
    assert "could not link yclid" in summary["latest"]["last_error"]


def test_fetch_upload_status_validates_response(monkeypatch) -> None:
    monkeypatch.setattr(ad_attribution, "_counter_id", lambda: 110783019)
    monkeypatch.setattr(
        metrica_reliability,
        "_authorized_json",
        lambda _url: {"uploading": {"id": 77, "status": "PROCESSED"}},
    )

    status = metrica_reliability.fetch_upload_status("77")

    assert status["id"] == 77
    assert status["status"] == "PROCESSED"


def test_upload_uses_current_yandex_endpoint_without_legacy_query(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b'{"uploading":{"id":88,"status":"PREPARED"}}'

    def fake_urlopen(request, timeout: int):
        captured["url"] = request.full_url
        captured["authorization"] = request.headers.get("Authorization", "")
        assert timeout == 20
        return Response()

    monkeypatch.setattr(ad_attribution, "_counter_id", lambda: 110783019)
    monkeypatch.setattr(ad_attribution, "_oauth_token", lambda: "secret-token")
    monkeypatch.setattr(metrica_upload_api, "urlopen", fake_urlopen)

    upload_id = metrica_upload_api.upload_conversion(
        {
            "yclid": "yclid-1",
            "target": "purchase_success",
            "event_time": 1_700_000_000,
            "price": 199,
            "currency": "RUB",
        }
    )

    assert upload_id == "88"
    assert captured["url"].endswith("/offline_conversions/upload")
    assert "client_id_type" not in captured["url"]
    assert captured["authorization"] == "OAuth secret-token"
