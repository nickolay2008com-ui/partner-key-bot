from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.message_retirement as retirement


def _labels(markup) -> list[str]:
    return [button.text for row in markup.inline_keyboard for button in row]


def test_active_topics_do_not_offer_messages() -> None:
    labels = _labels(retirement.active_topics_keyboard())
    assert all("сообщени" not in label.lower() for label in labels)
    assert any("отдельную тему" in label.lower() for label in labels)
    assert any("полная карта отношений" in label.lower() for label in labels)


def test_other_topics_show_all_current_products_without_messages_or_bridge() -> None:
    labels = _labels(retirement.other_topics_keyboard())

    assert labels == [
        "💗 Секреты любви\nВенера — 50 ₽",
        "🗣 Стиль общения\nМеркурий — 50 ₽",
        "🔥 Притяжение и инициатива\nМарс — 50 ₽",
        "🪐 Рост пары\nЮпитер — 50 ₽",
        "📖 Полная карта отношений — 199 ₽",
        "🔄 Новый разбор",
    ]
    assert all("сообщени" not in label.lower() for label in labels)
    assert all("эмоциональный мост" not in label.lower() for label in labels)


def test_old_message_button_is_redirected_to_current_topics(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Query:
        data = "message"
        message = object()

        async def answer(self) -> None:
            return None

    async def fake_remember(update) -> None:
        return None

    async def fake_track(update, event_name, **properties) -> None:
        calls.append({"event": event_name})

    async def fake_replace(update, context, text, **kwargs) -> None:
        calls.append({"text": text, "reply_markup": kwargs.get("reply_markup")})

    monkeypatch.setattr(retirement.base, "_remember_user", fake_remember)
    monkeypatch.setattr(retirement.base, "_track_event", fake_track)
    monkeypatch.setattr(retirement.base, "_tracked_replace_callback_text", fake_replace)

    update = SimpleNamespace(callback_query=Query())
    asyncio.run(retirement.retired_message_route(update, SimpleNamespace()))

    assert any(call.get("event") == "retired_message_product_opened" for call in calls)
    rendered = next(call for call in calls if "text" in call)
    assert "больше не используется" in str(rendered["text"])
    assert _labels(rendered["reply_markup"])[0] == "💗 Секреты любви\nВенера — 50 ₽"
    assert all("сообщени" not in label.lower() for label in _labels(rendered["reply_markup"]))
