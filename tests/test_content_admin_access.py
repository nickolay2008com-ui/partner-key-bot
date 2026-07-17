from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import app.content_admin_access as access
import app.woman_flow as base
from app.config import Settings


@pytest.fixture
def premium_keyboard(monkeypatch):
    monkeypatch.setattr(
        access,
        "_ORIGINAL_PREMIUM_KEYBOARD",
        lambda product_key, report_id=0: InlineKeyboardMarkup(
            [[InlineKeyboardButton("Купить", callback_data=f"buy:{product_key}:{report_id}")]]
        ),
    )


def _labels(markup: InlineKeyboardMarkup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_content_admin_ids_are_loaded_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("CONTENT_ADMIN_IDS", "101, 202")

    settings = Settings.from_env()

    assert settings.content_admin_ids == {101, 202}


@pytest.mark.parametrize(
    "product_key",
    ["details", "message", "planet_venus", "planet_mercury", "planet_mars", "planet_jupiter"],
)
def test_admin_button_is_available_on_every_premium_paywall(
    product_key: str,
    premium_keyboard,
    monkeypatch,
) -> None:
    monkeypatch.setattr(base, "settings", SimpleNamespace(content_admin_ids={101}))
    token = access._CURRENT_USER_ID.set(101)
    try:
        markup = access.premium_keyboard_with_admin(product_key, report_id=42)
    finally:
        access._CURRENT_USER_ID.reset(token)

    assert "🛠 Админ — открыть" in _labels(markup)
    admin_button = markup.inline_keyboard[1][0]
    assert admin_button.callback_data == f"admin:unlock:{product_key}:42"


def test_admin_button_is_hidden_from_regular_users(premium_keyboard, monkeypatch) -> None:
    monkeypatch.setattr(base, "settings", SimpleNamespace(content_admin_ids={101}))
    token = access._CURRENT_USER_ID.set(202)
    try:
        markup = access.premium_keyboard_with_admin("planet_jupiter", report_id=42)
    finally:
        access._CURRENT_USER_ID.reset(token)

    assert "🛠 Админ — открыть" not in _labels(markup)


def test_admin_unlock_grants_separate_entitlement(monkeypatch) -> None:
    granted = []
    events = []
    replies = []

    class Store:
        def grant_entitlement(self, *args):
            granted.append(args)

    class Query:
        data = "admin:unlock:planet_jupiter:42"

        async def answer(self, *args, **kwargs):
            return None

    async def activate_report_context(update, context, report_id):
        context.user_data[base.LAST_MAN_REPORT_ID] = report_id
        return True

    async def track_event(update, event_name, **properties):
        events.append((event_name, properties))

    async def replace_text(update, context, text, reply_markup=None):
        replies.append((text, reply_markup))

    monkeypatch.setattr(base, "settings", SimpleNamespace(content_admin_ids={101}))
    monkeypatch.setattr(base, "_activate_report_context", activate_report_context)
    monkeypatch.setattr(base, "get_product", lambda product_key: SimpleNamespace(key=product_key))
    monkeypatch.setattr(base, "get_store", lambda: Store())
    monkeypatch.setattr(base, "_track_event", track_event)
    monkeypatch.setattr(base, "_tracked_replace_callback_text", replace_text)
    monkeypatch.setattr(
        base,
        "detail_card_keyboard",
        lambda block, report_id=0: InlineKeyboardMarkup(
            [[InlineKeyboardButton(block, callback_data=f"open:{report_id}")]]
        ),
    )

    update = SimpleNamespace(
        callback_query=Query(),
        effective_user=SimpleNamespace(id=101),
    )
    context = SimpleNamespace(user_data={})

    asyncio.run(access.admin_unlock(update, context))

    assert granted == [(101, "planet_jupiter", 42, "admin:101")]
    assert events == [
        (
            "premium_admin_access_granted",
            {"product_key": "planet_jupiter", "report_id": 42, "provider": "admin"},
        )
    ]
    assert replies and "Админ-доступ открыт" in replies[0][0]
