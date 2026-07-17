from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

import app.button_contracts as contracts
import app.partner_flow as partner_flow
import app.woman_flow as base
from app.astro.report import PartnerReport
from app.config import Settings
from app.storage import ReportsStore


def _report() -> PartnerReport:
    placement = {
        "sign_key": "taurus",
        "sign_ru": "Телец",
        "element": "earth",
        "element_ru": "Земля",
        "is_retrograde": False,
    }
    return PartnerReport(
        partner_name="Тест",
        birth_date="1990-01-01",
        moon_status="stable",
        emotional_language="earth",
        emotional_language_title="Земля",
        placements={planet: dict(placement) for planet in ("moon", "venus", "mercury", "mars", "jupiter")},
        summary="",
        text="",
        message_templates=[],
    )


def test_content_admin_ids_are_loaded_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_ADMIN_IDS", "101, 202")

    settings = Settings.from_env()

    assert settings.content_admin_ids == {101, 202}


def test_admin_preview_button_is_visible_only_to_content_admin(monkeypatch) -> None:
    monkeypatch.setattr(
        base,
        "settings",
        SimpleNamespace(content_admin_ids={101}, webapp_url="https://example.test/webapp"),
    )

    admin_labels = [button.text for row in partner_flow.menu(101).inline_keyboard for button in row]
    buyer_labels = [button.text for row in partner_flow.menu(202).inline_keyboard for button in row]

    assert "🧪 Админ-просмотр" in admin_labels
    assert "🧪 Админ-просмотр" not in buyer_labels


def test_content_admin_opens_own_paid_html_without_fake_entitlement(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(101, _report())
    monkeypatch.setattr(base, "settings", SimpleNamespace(content_admin_ids={101}))
    monkeypatch.setattr(contracts.webapp, "get_store", lambda: store)

    text = contracts.detail_text_with_contract(101, "details", report_id)

    assert text
    assert store.has_entitlement(101, "details", report_id) is False


def test_regular_user_cannot_open_paid_html_without_purchase(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(202, _report())
    monkeypatch.setattr(base, "settings", SimpleNamespace(content_admin_ids={101}))
    monkeypatch.setattr(contracts.webapp, "get_store", lambda: store)

    with pytest.raises(ValueError, match="после оплаты"):
        contracts.detail_text_with_contract(202, "details", report_id)


def test_content_admin_passes_telegram_paid_gate_without_entitlement(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(101, _report())
    monkeypatch.setattr(base, "settings", SimpleNamespace(content_admin_ids={101}))
    monkeypatch.setattr(base, "get_store", lambda: store)
    update = SimpleNamespace(effective_user=SimpleNamespace(id=101))

    allowed = asyncio.run(contracts.has_premium_access_with_full_map(update, SimpleNamespace(), "details", report_id))

    assert allowed is True
    assert store.has_entitlement(101, "details", report_id) is False
