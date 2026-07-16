from __future__ import annotations

from pathlib import Path

from app.ad_attribution import AttributionStore, build_landing_html, conversion_csv


def test_attribution_store_binds_click_and_deduplicates_conversion(tmp_path: Path) -> None:
    store = AttributionStore(tmp_path / "analytics.sqlite3")
    token = store.create_click(
        "test-yclid-123",
        {
            "utm_source": "yandex",
            "utm_medium": "cpc",
            "utm_campaign": "launch",
        },
    )

    attribution = store.bind(token, 101)

    assert attribution is not None
    assert attribution["yclid"] == "test-yclid-123"
    assert store.latest_for_user(101)["token"] == token

    inserted = store.enqueue(
        event_key=f"bridge_received:101:{token}",
        user_id=101,
        yclid="test-yclid-123",
        target="bridge_received",
        event_time=1_700_000_000,
        price=None,
        currency=None,
    )
    duplicate = store.enqueue(
        event_key=f"bridge_received:101:{token}",
        user_id=101,
        yclid="test-yclid-123",
        target="bridge_received",
        event_time=1_700_000_001,
        price=None,
        currency=None,
    )

    assert inserted is True
    assert duplicate is False
    assert len(store.pending()) == 1


def test_conversion_csv_uses_yclid_offline_format() -> None:
    data = conversion_csv(
        {
            "yclid": "yclid-1",
            "target": "purchase_success",
            "event_time": 1_700_000_000,
            "price": 199,
            "currency": "RUB",
        }
    ).decode("utf-8")

    assert data.splitlines()[0] == "Yclid,Target,DateTime,Price,Currency"
    assert "yclid-1,purchase_success,1700000000,199.00,RUB" in data


def test_landing_contains_deep_link_and_metrica_goal() -> None:
    text = build_landing_html("https://t.me/example_bot?start=ad_token123", True)

    assert "https://t.me/example_bot?start=ad_token123" in text
    assert "landing_to_bot" in text
    assert "partner-yandex-metrica" in text
    assert "Рекламный переход сохранён" in text
