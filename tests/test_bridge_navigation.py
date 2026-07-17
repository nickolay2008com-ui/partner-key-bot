from __future__ import annotations

import asyncio

import app.bridge_navigation as navigation


def test_bridge_actions_keyboard_has_exactly_two_actions() -> None:
    keyboard = navigation.bridge_actions_keyboard().inline_keyboard

    assert len(keyboard) == 2
    assert keyboard[0][0].text == "💞 Открыть полный эмоциональный мост"
    assert keyboard[0][0].web_app is not None
    assert keyboard[1][0].text == "🧭 Посмотреть другие темы"
    assert keyboard[1][0].callback_data == "bridge:topics"


def test_other_topics_menu_does_not_repeat_bridge() -> None:
    keyboard = navigation.other_topics_keyboard().inline_keyboard
    labels = [button.text for row in keyboard for button in row]

    assert all("эмоциональный мост" not in label.lower() for label in labels)
    assert any("отдельную тему" in label.lower() for label in labels)
    assert any("полная карта отношений" in label.lower() for label in labels)


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
