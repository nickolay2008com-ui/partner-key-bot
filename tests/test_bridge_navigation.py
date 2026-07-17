from __future__ import annotations

import asyncio
from types import SimpleNamespace

import app.bridge_navigation as navigation


def test_bridge_actions_keyboard_has_exactly_two_actions() -> None:
    keyboard = navigation.bridge_actions_keyboard().inline_keyboard

    assert len(keyboard) == 2
    assert keyboard[0][0].text == "💞 Открыть полный эмоциональный мост"
    assert keyboard[0][0].web_app is not None
    assert keyboard[1][0].text == "🧭 Посмотреть другие темы"
    assert keyboard[1][0].callback_data == "bridge:topics"


def test_other_topics_menu_shows_every_current_option_directly() -> None:
    keyboard = navigation.other_topics_keyboard().inline_keyboard
    buttons = [button for row in keyboard for button in row]
    labels = [button.text for button in buttons]
    callbacks = [button.callback_data for button in buttons]

    assert len(keyboard) == 6
    assert all(len(row) == 1 for row in keyboard)
    assert labels == [
        "💗 Секреты любви (Венера) — 50 ₽",
        "🗣 Стиль общения (Меркурий) — 50 ₽",
        "🔥 Притяжение и инициатива (Марс) — 50 ₽",
        "🪐 Рост пары (Юпитер) — 50 ₽",
        "📖 Полная карта отношений — 199 ₽",
        "🔄 Новый разбор",
    ]
    assert callbacks == [
        "p:venus",
        "p:mercury",
        "p:mars",
        "p:jupiter",
        "p:full",
        "start_man",
    ]
    assert all("эмоциональный мост" not in label.lower() for label in labels)
    assert all("сообщени" not in label.lower() for label in labels)


def test_other_topics_text_does_not_duplicate_button_explanations(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Query:
        async def answer(self) -> None:
            return None

    async def fake_remember(update) -> None:
        return None

    async def fake_track(update, event_name, **properties) -> None:
        return None

    async def fake_reply(update, context, text, **kwargs) -> None:
        calls.append({"text": text, "reply_markup": kwargs.get("reply_markup")})

    monkeypatch.setattr(navigation.base, "_remember_user", fake_remember)
    monkeypatch.setattr(navigation.base, "_track_event", fake_track)
    monkeypatch.setattr(navigation.base, "_tracked_reply_text", fake_reply)

    asyncio.run(
        navigation.show_other_topics(
            SimpleNamespace(callback_query=Query()),
            SimpleNamespace(),
        )
    )

    assert len(calls) == 1
    assert calls[0]["text"] == "🧭 Основное меню"
    labels = [
        button.text
        for row in calls[0]["reply_markup"].inline_keyboard
        for button in row
    ]
    assert "Венера" in labels[0]
    assert "Меркурий" in labels[1]
    assert "Марс" in labels[2]
    assert "Юпитер" in labels[3]


def test_bridge_sender_does_not_send_automatic_menu(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    async def fake_send_long(update, context, text, **kwargs) -> None:
        calls.append({"text": text, "reply_markup": kwargs.get("reply_markup")})

    async def fail_reply(*args, **kwargs) -> None:
        raise AssertionError("The topics menu must not be sent automatically")

    monkeypatch.setattr(navigation.base, "_send_long", fake_send_long)
    monkeypatch.setattr(navigation.base, "_tracked_reply_text", fail_reply)

    asyncio.run(navigation.send_bridge_with_two_actions(object(), object(), "bridge text"))

    assert len(calls) == 1
    assert calls[0]["text"] == "bridge text"
    keyboard = calls[0]["reply_markup"].inline_keyboard
    assert len(keyboard) == 2
