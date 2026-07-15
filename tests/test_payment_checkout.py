from __future__ import annotations

import pytest

import app.payment_checkout as checkout
import app.payments as payments


def test_normalize_receipt_email() -> None:
    assert checkout.normalize_receipt_email("  Name@Yandex.RU ") == "name@yandex.ru"


@pytest.mark.parametrize("value", ["", "name", "name@", "@yandex.ru", "name@yandex"])
def test_normalize_receipt_email_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        checkout.normalize_receipt_email(value)


def test_yookassa_payment_contains_fiscal_receipt(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_request(shop_id: str, secret_key: str, method: str, url: str, body: dict | None = None) -> dict:
        captured["body"] = body or {}
        return {
            "id": "payment-1",
            "status": "pending",
            "paid": False,
            "confirmation": {"confirmation_url": "https://yookassa.ru/pay/payment-1"},
            "metadata": {
                "product_key": "planet_venus",
                "report_id": "7",
                "telegram_user_id": "42",
            },
        }

    monkeypatch.setattr(payments, "_yookassa_request", fake_request)
    product = payments.get_product("planet_venus")
    assert product is not None

    result = checkout.create_yookassa_payment_with_receipt(
        shop_id="shop",
        secret_key="secret",
        product=product,
        product_key="planet_venus",
        report_id=7,
        user_id=42,
        return_url="https://example.com/webapp",
        receipt_email="buyer@example.com",
    )

    body = captured["body"]
    assert isinstance(body, dict)
    assert body["receipt"]["customer"] == {"email": "buyer@example.com"}
    item = body["receipt"]["items"][0]
    assert item["amount"] == {"value": "50.00", "currency": "RUB"}
    assert item["quantity"] == "1.00"
    assert item["vat_code"] == 1
    assert item["payment_mode"] == "full_payment"
    assert item["payment_subject"] == "service"
    assert result.payment_id == "payment-1"
    assert result.confirmation_url == "https://yookassa.ru/pay/payment-1"
