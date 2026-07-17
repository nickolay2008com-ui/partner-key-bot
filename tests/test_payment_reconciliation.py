from __future__ import annotations

from decimal import Decimal

import app.payment_reconciliation as reconciliation
import app.payments as payments


def _payment(
    *,
    product_key: str = "planet_venus",
    value: str = "50.00",
    status: str = "succeeded",
    paid: bool = True,
) -> dict[str, object]:
    return {
        "id": "payment-1",
        "status": status,
        "paid": paid,
        "amount": {"value": value, "currency": "RUB"},
        "metadata": {
            "product_key": product_key,
            "report_id": "7",
            "telegram_user_id": "42",
        },
    }


def test_validated_purchase_accepts_completed_matching_payment() -> None:
    assert reconciliation._validated_purchase(_payment()) == (
        "payment-1",
        42,
        "planet_venus",
        7,
    )


def test_validated_purchase_rejects_pending_payment() -> None:
    assert reconciliation._validated_purchase(_payment(status="pending", paid=False)) is None


def test_validated_purchase_rejects_wrong_amount() -> None:
    assert reconciliation._validated_purchase(_payment(value="49.00")) is None


def test_validated_purchase_rejects_unknown_product() -> None:
    assert reconciliation._validated_purchase(_payment(product_key="planet_saturn")) is None


def test_list_recent_payments_uses_yookassa_collection(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(
        shop_id: str,
        secret_key: str,
        method: str,
        url: str,
        body: dict | None = None,
    ) -> dict[str, object]:
        captured.update(
            {
                "shop_id": shop_id,
                "secret_key": secret_key,
                "method": method,
                "url": url,
                "body": body,
            }
        )
        return {"items": [_payment()]}

    monkeypatch.setattr(payments, "_yookassa_request", fake_request)

    items = reconciliation._list_recent_payments(
        shop_id="shop",
        secret_key="secret",
        limit=100,
    )

    assert len(items) == 1
    assert captured["method"] == "GET"
    assert str(captured["url"]).startswith(payments.YOOKASSA_API_URL + "?")
    assert "limit=100" in str(captured["url"])
    assert captured["body"] is None


def test_receipt_note_distinguishes_test_payment() -> None:
    note = reconciliation._receipt_note({"test": True})
    assert "тестовый платёж" in note
    assert "чек" in note


def test_product_prices_are_compared_as_decimal() -> None:
    product = payments.get_product("planet_venus")
    assert product is not None
    assert Decimal(product.rub_amount) == Decimal("50.00")
