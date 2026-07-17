from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import app.payment_checkout as checkout
import app.payments as payments
import app.woman_flow as base


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



def test_email_prompt_returns_to_exact_planet_paywall() -> None:
    keyboard = checkout._email_prompt_keyboard(base, "planet_jupiter", 42)

    button = keyboard.inline_keyboard[0][0]
    assert button.text == "← Вернуться к разбору"
    assert button.callback_data == "premium:planet:jupiter:42"


def test_email_prompt_return_deletes_placeholder_and_restores_previous_menu(monkeypatch) -> None:
    calls: list[str] = []
    events: list[tuple[str, dict]] = []

    class Message:
        async def delete(self) -> None:
            calls.append("delete")

    class Query:
        data = "premium:planet:jupiter:42"
        message = Message()

    async def original_premium_offer(update, context) -> None:
        calls.append("open_previous")

    async def original_premium_buy(update, context) -> None:
        return None

    async def original_unknown_text(update, context) -> None:
        return None

    def original_clear_flow_state(context) -> None:
        return None

    async def track_event(update, event_name, **properties) -> None:
        events.append((event_name, properties))

    fake_base = SimpleNamespace(
        premium_offer=original_premium_offer,
        premium_buy=original_premium_buy,
        unknown_text=original_unknown_text,
        _clear_flow_state=original_clear_flow_state,
        _callback_report=base._callback_report,
        _callback_with_report=base._callback_with_report,
        planet_product_key_to_block=base.planet_product_key_to_block,
        PLANET_PAYWALL_COPY=base.PLANET_PAYWALL_COPY,
        _forget_bot_message=lambda context, message: calls.append("forget"),
        _track_event=track_event,
        logger=base.logger,
    )
    checkout.install(fake_base)

    context = SimpleNamespace(
        user_data={
            checkout.PENDING_RECEIPT_PRODUCT: "planet_jupiter",
            checkout.PENDING_RECEIPT_REPORT_ID: 42,
        }
    )
    update = SimpleNamespace(callback_query=Query())

    asyncio.run(fake_base.premium_offer(update, context))

    assert calls == ["delete", "forget", "open_previous"]
    assert checkout.PENDING_RECEIPT_PRODUCT not in context.user_data
    assert checkout.PENDING_RECEIPT_REPORT_ID not in context.user_data
    assert events == [
        (
            "receipt_email_prompt_closed",
            {"destination": "premium:planet:jupiter"},
        )
    ]
