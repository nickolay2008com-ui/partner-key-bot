from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.payment_checkout as checkout
import app.payment_reconciliation as protection
import app.payments as payments
from app.astro.report import PartnerReport
from app.storage import ReportsStore


def _report(name: str = "Алексей") -> PartnerReport:
    moon = {
        "sign_key": "taurus",
        "sign_ru": "Телец",
        "element": "earth",
        "element_ru": "Земля",
        "is_retrograde": False,
    }
    return PartnerReport(
        partner_name=name,
        birth_date="1990-01-01",
        moon_status="stable",
        emotional_language="earth",
        emotional_language_title="Земля",
        placements={planet: dict(moon) for planet in ("moon", "venus", "mercury", "mars", "jupiter")},
        summary="",
        text="",
        message_templates=[],
    )


def test_delivery_claim_is_atomic_and_delivered_payment_cannot_be_claimed_again(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")

    first = protection._claim_delivery(
        store,
        payment_id="pay-1",
        user_id=7,
        product_key="details",
        report_id=42,
    )
    second = protection._claim_delivery(
        store,
        payment_id="pay-1",
        user_id=7,
        product_key="details",
        report_id=42,
    )
    protection._record_delivery(
        store,
        payment_id="pay-1",
        user_id=7,
        product_key="details",
        report_id=42,
        status="delivered",
    )
    third = protection._claim_delivery(
        store,
        payment_id="pay-1",
        user_id=7,
        product_key="details",
        report_id=42,
    )

    assert first == "claimed"
    assert second == "processing"
    assert third == "already_delivered"


def test_checkout_sessions_are_durable_reconciliation_sources(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    checkout.save_checkout_session(store, 7, "details", 42, "pay-1", "https://yookassa.ru/pay/pay-1")

    assert checkout.list_checkout_sessions(store) == [
        {
            "user_id": 7,
            "product_key": "details",
            "report_id": 42,
            "payment_id": "pay-1",
            "confirmation_url": "https://yookassa.ru/pay/pay-1",
            "updated_at": checkout.list_checkout_sessions(store)[0]["updated_at"],
        }
    ]


def test_reconciliation_uses_saved_session_when_recent_payment_list_is_unavailable(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    checkout.save_checkout_session(store, 7, "details", 42, "pay-1", "https://yookassa.ru/pay/pay-1")
    monkeypatch.setattr(protection.base, "get_store", lambda: store)
    monkeypatch.setattr(
        protection.base,
        "settings",
        SimpleNamespace(yookassa_enabled=True, yookassa_shop_id="shop", yookassa_secret_key="secret"),
    )
    monkeypatch.setattr(protection, "_RECONCILE_LOCK", None)
    monkeypatch.setattr(
        protection,
        "_list_recent_payments",
        lambda **kwargs: (_ for _ in ()).throw(payments.YooKassaPaymentError("error", "offline")),
    )
    monkeypatch.setattr(
        protection,
        "_get_payment_raw",
        lambda **kwargs: {"id": "pay-1", "status": "pending", "paid": False},
    )

    summary = asyncio.run(protection.reconcile_recent_payments(SimpleNamespace()))

    assert summary["api_error"] == 1
    assert summary["pending"] == 1
    assert summary["scanned"] == 1


def test_entitlements_are_listed_for_buyer_self_service_recovery(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(7, _report())
    store.grant_entitlement(7, "details", report_id, "pay-1")

    purchases = store.list_entitlements(7)
    keyboard = protection._purchases_keyboard(store, 7)

    assert purchases[0]["product_key"] == "details"
    assert purchases[0]["payment_payload"] == "pay-1"
    assert keyboard.inline_keyboard[0][0].callback_data == f"purchase:open:details:{report_id}"
    assert "Алексей" in keyboard.inline_keyboard[0][0].text


def test_payment_incident_is_durable_until_admin_resolves_it(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    protection._record_incident(
        store,
        reference_id="yookassa:pay-1",
        provider="yookassa",
        user_id=7,
        reason="report_not_found",
        payload={"report_id": 42},
    )

    assert protection._list_open_incidents(store)[0]["reference_id"] == "yookassa:pay-1"

    protection._resolve_incident(store, "yookassa:pay-1")

    assert protection._list_open_incidents(store) == []


def test_yookassa_metadata_payload_must_match_product_and_report() -> None:
    payment = {
        "id": "pay-1",
        "status": "succeeded",
        "paid": True,
        "amount": {"value": "199.00", "currency": "RUB"},
        "metadata": {
            "product_key": "details",
            "report_id": "42",
            "telegram_user_id": "7",
            "payload": payments.make_payload("details", 99),
        },
    }

    assert protection._validated_purchase(payment) is None


def test_successful_stars_payment_grants_access_and_delivers_product(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(7, _report())
    product = payments.get_product("message")
    assert product is not None
    monkeypatch.setattr(protection.base, "get_store", lambda: store)
    monkeypatch.setattr(
        protection.base,
        "settings",
        SimpleNamespace(broadcast_admin_ids=set(), authorized_telegram_ids=set()),
    )

    sent: list[dict[str, object]] = []

    class Bot:
        async def send_message(self, **kwargs):
            sent.append(kwargs)

    successful = SimpleNamespace(
        telegram_payment_charge_id="charge-1",
        provider_payment_charge_id="provider-1",
        invoice_payload=payments.make_payload("message", report_id),
        currency=payments.CURRENCY_STARS,
        total_amount=product.stars,
    )
    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_message=SimpleNamespace(successful_payment=successful),
    )
    context = SimpleNamespace(application=SimpleNamespace(bot=Bot()))

    asyncio.run(protection._protected_successful_payment(update, context))

    assert store.has_entitlement(7, "message", report_id) is True
    assert protection._delivery_status(store, "stars:charge-1") == "delivered"
    assert any("Оплата подтверждена" in str(item["text"]) for item in sent)


def test_main_menu_exposes_permanent_purchase_recovery() -> None:
    labels = [button.text for row in protection.base.menu().inline_keyboard for button in row]
    assert "🛟 Мои покупки" in labels
