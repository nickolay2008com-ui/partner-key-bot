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
        "💗 Секреты любви\nВенера — 50 ₽",
        "🗣 Стиль общения\nМеркурий — 50 ₽",
        "🔥 Притяжение и инициатива\nМарс — 50 ₽",
        "🪐 Рост пары\nЮпитер — 50 ₽",
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
    assert all("(" not in label and ")" not in label for label in labels[:4])
    assert all(label.count("\n") == 1 for label in labels[:4])


def test_other_topics_text_does_not_duplicate_button_explanations(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Message:
        async def delete(self) -> None:
            raise AssertionError("The bridge summary must remain visible")

    class Query:
        data = "bridge:topics"
        message = Message()

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
    assert labels[0].splitlines() == ["💗 Секреты любви", "Венера — 50 ₽"]
    assert labels[1].splitlines() == ["🗣 Стиль общения", "Меркурий — 50 ₽"]
    assert labels[2].splitlines() == ["🔥 Притяжение и инициатива", "Марс — 50 ₽"]
    assert labels[3].splitlines() == ["🪐 Рост пары", "Юпитер — 50 ₽"]


def test_legacy_planets_button_opens_main_menu_without_compact_screen(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    class Message:
        async def delete(self) -> None:
            calls.append({"action": "deleted", "message": self})

    class Query:
        data = "premium:planets"

        def __init__(self) -> None:
            self.message = Message()

        async def answer(self) -> None:
            return None

    async def fake_remember(update) -> None:
        return None

    async def fake_track(update, event_name, **properties) -> None:
        calls.append({"event": event_name, "properties": properties})

    async def fake_reply(update, context, text, **kwargs) -> None:
        calls.append({"text": text, "reply_markup": kwargs.get("reply_markup")})

    def fake_forget(context, message) -> None:
        calls.append({"action": "forgotten", "message": message})

    async def fail_original_handler(update, context) -> None:
        raise AssertionError("The obsolete compact planets screen must not open")

    query = Query()
    context = SimpleNamespace()
    monkeypatch.setattr(navigation.base, "_remember_user", fake_remember)
    monkeypatch.setattr(navigation.base, "_track_event", fake_track)
    monkeypatch.setattr(navigation.base, "_tracked_reply_text", fake_reply)
    monkeypatch.setattr(navigation.base, "_forget_bot_message", fake_forget)
    monkeypatch.setattr(navigation, "_ORIGINAL_PREMIUM_OFFER", fail_original_handler)

    asyncio.run(
        navigation.premium_offer_with_main_menu(
            SimpleNamespace(callback_query=query),
            context,
        )
    )

    rendered = next(call for call in calls if "text" in call)
    assert rendered["text"] == "🧭 Основное меню"
    labels = [
        button.text
        for row in rendered["reply_markup"].inline_keyboard
        for button in row
    ]
    assert labels[0].startswith("💗 Секреты любви\nВенера")
    assert "📖 Всё меню" not in labels
    assert all("Выберите планету" not in str(call.get("text", "")) for call in calls)
    tracked = next(call for call in calls if call.get("event"))
    assert tracked["properties"]["source"] == "premium_planets"

    deleted_index = next(index for index, call in enumerate(calls) if call.get("action") == "deleted")
    forgotten_index = next(index for index, call in enumerate(calls) if call.get("action") == "forgotten")
    rendered_index = calls.index(rendered)
    assert deleted_index < forgotten_index < rendered_index
    assert calls[deleted_index]["message"] is query.message
    assert calls[forgotten_index]["message"] is query.message


def test_other_premium_callbacks_stay_on_existing_handler(monkeypatch) -> None:
    calls: list[str] = []

    class Query:
        data = "premium:details"

    async def fake_original_handler(update, context) -> None:
        calls.append(update.callback_query.data)

    monkeypatch.setattr(navigation, "_ORIGINAL_PREMIUM_OFFER", fake_original_handler)

    asyncio.run(
        navigation.premium_offer_with_main_menu(
            SimpleNamespace(callback_query=Query()),
            SimpleNamespace(),
        )
    )

    assert calls == ["premium:details"]


def test_planet_cards_use_main_menu_button_in_every_payment_state() -> None:
    markups = [
        navigation.premium_keyboard_with_main_menu("planet_venus"),
        navigation.yookassa_payment_keyboard_with_main_menu(
            "planet_venus",
            "payment-id",
            "https://example.test/pay",
        ),
        navigation.payment_recovery_keyboard_with_main_menu(
            "planet_venus",
            "payment-id",
        ),
    ]

    for markup in markups:
        buttons = [button for row in markup.inline_keyboard for button in row]
        main_menu_buttons = [
            button for button in buttons if button.callback_data == "premium:planets"
        ]

        assert len(main_menu_buttons) == 1
        assert main_menu_buttons[0].text == "🧭 Главное меню"
        assert all(button.text != "⬅️ К планетам" for button in buttons)


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
