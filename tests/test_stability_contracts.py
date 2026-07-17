from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from app import bridge_navigation, payment_checkout, payments, webapp, woman_flow
from app.storage import ReportsStore


def test_report_bound_callbacks_remain_backward_compatible() -> None:
    assert woman_flow._callback_with_report("p:full") == "p:full"
    assert woman_flow._callback_with_report("p:full", 42) == "p:full:42"
    assert woman_flow._callback_report("p:full") == ("p:full", 0)
    assert woman_flow._callback_report("p:full:42") == ("p:full", 42)


def test_current_topics_bind_every_paid_action_to_the_report() -> None:
    keyboard = bridge_navigation.other_topics_keyboard(42)
    callbacks = [button.callback_data for row in keyboard.inline_keyboard for button in row if button.callback_data]

    assert callbacks[:-1] == ["p:venus:42", "p:mercury:42", "p:mars:42", "p:jupiter:42", "p:full:42"]


def test_detail_webapp_url_is_bound_to_the_report() -> None:
    assert woman_flow.detail_webapp_info("full", 42).url.endswith("/webapp/detail/full?report_id=42")


def test_checkout_session_is_reused_and_can_be_replaced(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")

    payment_checkout.save_checkout_session(store, 7, "details", 42, "pay-1", "https://pay.test/1")
    assert payment_checkout.get_checkout_session(store, 7, "details", 42) == {
        "payment_id": "pay-1",
        "confirmation_url": "https://pay.test/1",
    }

    payment_checkout.save_checkout_session(store, 7, "details", 42, "pay-2", "https://pay.test/2")
    assert payment_checkout.get_checkout_session(store, 7, "details", 42) == {
        "payment_id": "pay-2",
        "confirmation_url": "https://pay.test/2",
    }

    payment_checkout.delete_checkout_session(store, 7, "details", 42)
    assert payment_checkout.get_checkout_session(store, 7, "details", 42) is None


def test_pending_checkout_returns_the_existing_payment_link(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    payment_checkout.save_checkout_session(store, 7, "details", 42, "pay-1", "https://pay.test/1")
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        payments,
        "get_yookassa_payment",
        lambda **kwargs: payments.YooKassaPayment(
            payment_id="pay-1",
            status="pending",
            confirmation_url="https://pay.test/1",
            paid=False,
        ),
    )

    class Base:
        PENDING_YOOKASSA_PAYMENT = "pending"
        PLANET_PAYWALL_COPY: dict[str, object] = {}
        settings = SimpleNamespace(yookassa_shop_id="shop", yookassa_secret_key="secret")

        @staticmethod
        def get_store():
            return store

        @staticmethod
        async def _track_event(update, event_name, **properties):
            calls.append({"event": event_name, "properties": properties})

        @staticmethod
        async def _tracked_replace_callback_text(update, context, text, **kwargs):
            calls.append({"text": text, "reply_markup": kwargs.get("reply_markup")})

        @staticmethod
        def yookassa_payment_keyboard(product_key, payment_id, confirmation_url, report_id):
            return product_key, payment_id, confirmation_url, report_id

        @staticmethod
        def compact_planets_keyboard(report_id):
            return report_id

        @staticmethod
        def after_bridge_keyboard(report_id):
            return report_id

    context = SimpleNamespace(user_data={})
    reused = asyncio.run(
        payment_checkout._reuse_checkout_if_possible(
            Base,
            object(),
            context,
            product_key="details",
            report_id=42,
            user_id=7,
        )
    )

    assert reused is True
    assert context.user_data["pending"]["payment_id"] == "pay-1"
    assert any(call.get("event") == "premium_yookassa_payment_reused" for call in calls)
    assert calls[-1]["reply_markup"] == ("details", "pay-1", "https://pay.test/1", 42)


def _signed_init_data(token: str, auth_date: int) -> str:
    pairs = {
        "auth_date": str(auth_date),
        "query_id": "query-1",
        "user": json.dumps({"id": 7}, separators=(",", ":")),
    }
    check = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", token.encode(), hashlib.sha256).digest()
    pairs["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(pairs)


def test_webapp_rejects_stale_telegram_authorization(monkeypatch) -> None:
    token = "test-token"
    monkeypatch.setattr(webapp, "settings", SimpleNamespace(telegram_bot_token=token))

    assert webapp._validate_init_data(_signed_init_data(token, int(time.time()))) == 7
    with pytest.raises(ValueError, match="устарела"):
        webapp._validate_init_data(_signed_init_data(token, int(time.time()) - 90000))


def test_paid_detail_cache_is_scoped_by_report() -> None:
    assert "partner-key-detail:${reportId}:${block}:v10" in webapp.DETAIL_WEBAPP_HTML
    assert "if (!cacheKey) return false" in webapp.DETAIL_WEBAPP_HTML
