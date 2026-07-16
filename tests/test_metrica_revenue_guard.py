from __future__ import annotations

from app import ad_attribution, metrica_revenue_guard


class FakeStore:
    def __init__(self) -> None:
        self.rows: list[dict] = []

    def latest_for_user(self, _user_id: int) -> dict:
        return {"yclid": "yclid-1", "token": "token-1"}

    def enqueue(self, **kwargs):
        self.rows.append(kwargs)
        return True


class Product:
    rubles = 149


class Base:
    @staticmethod
    def get_product(_product_key: str):
        return Product()


def test_payment_started_does_not_report_revenue(monkeypatch) -> None:
    store = FakeStore()
    monkeypatch.setattr(ad_attribution, "get_store", lambda: store)
    monkeypatch.setattr(ad_attribution, "flush_pending", lambda: 0)
    monkeypatch.setattr(metrica_revenue_guard.threading, "Thread", lambda **_kwargs: type("T", (), {"start": lambda self: None})())

    metrica_revenue_guard.enqueue_conversion(
        Base,
        user_id=1,
        target="payment_started",
        properties={"product_key": "message", "report_id": 10},
    )

    assert store.rows[0]["price"] is None
    assert store.rows[0]["currency"] is None


def test_purchase_success_reports_confirmed_revenue(monkeypatch) -> None:
    store = FakeStore()
    monkeypatch.setattr(ad_attribution, "get_store", lambda: store)
    monkeypatch.setattr(ad_attribution, "flush_pending", lambda: 0)
    monkeypatch.setattr(metrica_revenue_guard.threading, "Thread", lambda **_kwargs: type("T", (), {"start": lambda self: None})())

    metrica_revenue_guard.enqueue_conversion(
        Base,
        user_id=1,
        target="purchase_success",
        properties={"product_key": "message", "report_id": 10},
    )

    assert store.rows[0]["price"] == 149.0
    assert store.rows[0]["currency"] == "RUB"
