import asyncio
from types import SimpleNamespace

from app import partner_flow
from app import woman_flow
from app.storage import ReportsStore


class _StoredReport:
    def to_dict(self) -> dict[str, str]:
        return {
            "partner_name": "Андрей",
            "birth_date": "1990-01-01",
            "emotional_language": "earth",
            "emotional_language_title": "Язык спокойствия",
        }


def _buttons(has_saved_reports: bool) -> list[tuple[str, str | None]]:
    keyboard = partner_flow.welcome_menu(has_saved_reports)
    return [
        (button.text, button.callback_data)
        for row in keyboard.inline_keyboard
        for button in row
    ]


def test_new_user_sees_only_free_first_key() -> None:
    assert _buttons(has_saved_reports=False) == [
        ("🔑 Получить первый ключ бесплатно", "start_man"),
    ]


def test_returning_user_can_start_again_or_open_history() -> None:
    assert _buttons(has_saved_reports=True) == [
        ("🔑 Начать новый разбор", "start_man"),
        ("🗂 Мои разборы", "history"),
    ]


def test_only_a_completed_stored_report_enables_history(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    store.register_user(101)

    assert store.has_saved_reports(101) is False

    store.add(101, _StoredReport())

    assert store.has_saved_reports(101) is True


def test_start_uses_saved_report_state_for_welcome_menu(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _Store:
        @staticmethod
        def has_saved_reports(user_id: int) -> bool:
            assert user_id == 101
            return True

    class _Message:
        async def reply_text(self, text: str, *, reply_markup: object) -> None:
            captured["text"] = text
            captured["reply_markup"] = reply_markup

    async def _noop(*_args: object, **_kwargs: object) -> None:
        return None

    monkeypatch.setattr(woman_flow, "_is_authorized", lambda _update: True)
    monkeypatch.setattr(woman_flow, "_remember_user", _noop)
    monkeypatch.setattr(woman_flow, "_set_chat_menu_button", _noop)
    monkeypatch.setattr(woman_flow, "_clear_flow_state", lambda _context: None)
    monkeypatch.setattr(woman_flow, "_track_event", _noop)
    monkeypatch.setattr(woman_flow, "_user_id", lambda _update: 101)
    monkeypatch.setattr(woman_flow, "get_store", _Store)

    update = SimpleNamespace(callback_query=None, effective_message=_Message())
    context = SimpleNamespace(user_data={})
    asyncio.run(woman_flow.start(update, context))

    keyboard = captured["reply_markup"]
    assert [button.text for row in keyboard.inline_keyboard for button in row] == [
        "🔑 Начать новый разбор",
        "🗂 Мои разборы",
    ]


def test_regular_menu_keeps_service_routes() -> None:
    buttons = [
        (button.text, button.callback_data)
        for row in partner_flow.menu().inline_keyboard
        for button in row
    ]

    assert ("🛟 Мои покупки", "purchases") in buttons
    assert any(text == "👤 Мои данные" for text, _ in buttons)
