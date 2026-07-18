from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app import partner_flow, webapp, woman_flow
from app.astro.report import PartnerReport
from app.storage import ReportsStore


def _report(name: str = "Партнёр", birth_date: str = "1990-01-01") -> PartnerReport:
    return PartnerReport(
        partner_name=name,
        birth_date=birth_date,
        moon_status="exact",
        emotional_language="earth",
        emotional_language_title="Язык спокойствия",
        placements={"moon": {"sign_ru": "Телец", "element": "earth", "element_ru": "Земля"}},
        summary=f"{name}: summary",
        text=f"report for {name}",
        message_templates=[],
    )


def test_launch_token_is_idempotent_but_same_date_can_be_started_again(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")

    first_id, first_created = store.add_idempotent(7, _report(), "launch-one")
    retry_id, retry_created = store.add_idempotent(7, _report(), "launch-one")
    second_id, second_created = store.add_idempotent(7, _report(), "launch-two")

    assert (retry_id, retry_created) == (first_id, False)
    assert first_created is True
    assert second_created is True
    assert second_id != first_id
    assert len(store.recent(7)) == 2


def test_result_keyboard_keeps_optional_name_and_history() -> None:
    buttons = [
        (button.text, button.callback_data)
        for row in partner_flow.after_free_deep_keyboard(42, offer_name=True).inline_keyboard
        for button in row
    ]

    assert ("✍️ Добавить имя к этому разбору", "report:name:42") in buttons
    assert ("🗂 Мои разборы", "history") in buttons


def test_saved_partner_choice_can_be_cancelled() -> None:
    buttons = [
        (button.text, button.callback_data)
        for row in woman_flow.profile_partner_keyboard("Алексей", "14.08.1987").inline_keyboard
        for button in row
    ]

    assert ("Отмена", "cancel") in buttons


def test_followup_keeps_history_available_after_optional_name() -> None:
    buttons = [
        (button.text, button.callback_data)
        for row in woman_flow.after_free_followup_keyboard().inline_keyboard
        for button in row
    ]

    assert ("🗂 Мои разборы", "history") in buttons


def test_new_entry_promises_date_only_and_tracks_prompt_contract(monkeypatch) -> None:
    events: list[str] = []
    messages: list[str] = []

    async def _noop(*_args, **_kwargs) -> None:
        return None

    async def _track(_update, event_name: str, **_properties) -> None:
        events.append(event_name)

    async def _profile(_update) -> dict[str, str]:
        return {"partner_name": "", "partner_birth_date": ""}

    async def _reply(_update, _context, text: str, **_kwargs):
        messages.append(text)
        return None

    monkeypatch.setattr(woman_flow, "_is_authorized", lambda _update: True)
    monkeypatch.setattr(woman_flow, "_remember_user", _noop)
    monkeypatch.setattr(woman_flow, "_track_event", _track)
    monkeypatch.setattr(woman_flow, "_set_chat_menu_button", _noop)
    monkeypatch.setattr(woman_flow, "_clear_active_bot_messages", _noop)
    monkeypatch.setattr(woman_flow, "_get_profile", _profile)
    monkeypatch.setattr(woman_flow, "_tracked_reply_text", _reply)

    update = SimpleNamespace(callback_query=None)
    context = SimpleNamespace(user_data={})
    state = asyncio.run(woman_flow.start_man(update, context))

    assert state == woman_flow.ASK_MAN_DATE
    assert {"first_key_clicked", "birthdate_prompt_shown"}.issubset(events)
    assert "Мои разборы" in messages[-1]
    assert "Мои данные" in messages[-1]
    assert "Имя" not in messages[-1]


def test_invalid_birthdate_tracks_submission_and_stays_on_date_step(monkeypatch) -> None:
    events: list[str] = []

    async def _track(_update, event_name: str, **_properties) -> None:
        events.append(event_name)

    async def _reply(*_args, **_kwargs):
        return None

    monkeypatch.setattr(woman_flow, "_track_event", _track)
    monkeypatch.setattr(woman_flow, "_tracked_reply_text", _reply)

    update = SimpleNamespace(effective_message=SimpleNamespace(chat_id=7))
    context = SimpleNamespace(user_data={})
    state = asyncio.run(woman_flow._build_man_report_from_date(update, context, "", "не дата"))

    assert state == woman_flow.ASK_MAN_DATE
    assert events == ["birthdate_submitted", "birthdate_invalid"]


def test_unnamed_preview_uses_grammatical_neutral_title() -> None:
    text = partner_flow.format_free_preview(_report())

    assert text.startswith("🔑 Первый ключ к вашему мужчине")
    assert "ключ к Мужчина" not in text


def test_generation_retries_storage_once_and_tracks_send_after_delivery(monkeypatch) -> None:
    ordered: list[str] = []
    save_calls = 0

    class _Wait:
        async def delete(self) -> None:
            return None

        async def edit_text(self, _text: str) -> None:
            return None

    async def _reply(*_args, **_kwargs):
        return _Wait()

    async def _track(_update, event_name: str, **_properties) -> None:
        ordered.append(event_name)

    async def _store(*_args, **_kwargs):
        nonlocal save_calls
        save_calls += 1
        if save_calls == 1:
            raise RuntimeError("temporary storage error")
        return 42, True

    async def _send(*_args, **_kwargs) -> None:
        ordered.append("telegram_send")

    monkeypatch.setattr(woman_flow, "calculate_partner_chart", lambda _date: object())
    monkeypatch.setattr(woman_flow, "build_partner_report", lambda _chart, _name: _report())
    monkeypatch.setattr(woman_flow, "_tracked_reply_text", _reply)
    monkeypatch.setattr(woman_flow, "_track_event", _track)
    monkeypatch.setattr(woman_flow, "_store_free_report_once", _store)
    monkeypatch.setattr(woman_flow, "_save_partner_profile_safely", lambda *_args, **_kwargs: asyncio.sleep(0, result=True))
    monkeypatch.setattr(woman_flow, "_send_long", _send)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_message=SimpleNamespace(chat_id=7),
    )
    context = SimpleNamespace(
        user_data={woman_flow.FREE_REPORT_LAUNCH_TOKEN: "launch"},
        bot=SimpleNamespace(send_chat_action=lambda **_kwargs: asyncio.sleep(0)),
    )

    result = asyncio.run(woman_flow._build_man_report_from_date(update, context, "", "12.04.1993"))

    assert result == woman_flow.ConversationHandler.END
    assert save_calls == 2
    assert "report_saved" in ordered
    assert ordered.index("telegram_send") < ordered.index("free_report_sent")


def test_free_report_sent_is_not_tracked_when_telegram_delivery_fails(monkeypatch) -> None:
    events: list[str] = []

    class _Wait:
        async def delete(self) -> None:
            return None

    async def _reply(*_args, **_kwargs):
        return _Wait()

    async def _track(_update, event_name: str, **_properties) -> None:
        events.append(event_name)

    async def _failed_send(*_args, **_kwargs) -> None:
        raise RuntimeError("telegram unavailable")

    monkeypatch.setattr(woman_flow, "calculate_partner_chart", lambda _date: object())
    monkeypatch.setattr(woman_flow, "build_partner_report", lambda _chart, _name: _report())
    monkeypatch.setattr(woman_flow, "_tracked_reply_text", _reply)
    monkeypatch.setattr(woman_flow, "_track_event", _track)
    monkeypatch.setattr(woman_flow, "_store_free_report_once", lambda *_args, **_kwargs: asyncio.sleep(0, result=(42, True)))
    monkeypatch.setattr(woman_flow, "_save_partner_profile_safely", lambda *_args, **_kwargs: asyncio.sleep(0, result=True))
    monkeypatch.setattr(woman_flow, "_send_long", _failed_send)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_message=SimpleNamespace(chat_id=7),
    )
    context = SimpleNamespace(
        user_data={woman_flow.FREE_REPORT_LAUNCH_TOKEN: "launch"},
        bot=SimpleNamespace(send_chat_action=lambda **_kwargs: asyncio.sleep(0)),
    )

    with pytest.raises(RuntimeError, match="telegram unavailable"):
        asyncio.run(woman_flow._build_man_report_from_date(update, context, "", "12.04.1993"))

    assert "free_report_sent" not in events


def test_naming_old_report_does_not_overwrite_latest_profile(tmp_path, monkeypatch) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    old_id = store.add(7, _report("Партнёр", "1990-01-01"))
    store.add(7, _report("Новый", "1991-02-02"))
    store.save_profile(7, {"partner_name": "Новый", "partner_birth_date": "02.02.1991"})

    async def _reply(*_args, **_kwargs):
        return None

    async def _track(*_args, **_kwargs) -> None:
        return None

    monkeypatch.setattr(woman_flow, "get_store", lambda: store)
    monkeypatch.setattr(woman_flow, "calculate_partner_chart", lambda _date: object())
    monkeypatch.setattr(woman_flow, "build_partner_report", lambda _chart, name: _report(name, "1990-01-01"))
    monkeypatch.setattr(woman_flow, "_tracked_reply_text", _reply)
    monkeypatch.setattr(woman_flow, "_track_event", _track)

    update = SimpleNamespace(
        effective_user=SimpleNamespace(id=7),
        effective_message=SimpleNamespace(text="Старый"),
    )
    context = SimpleNamespace(user_data={woman_flow.PENDING_REPORT_NAME_ID: old_id})

    asyncio.run(woman_flow.save_optional_man_name(update, context))

    assert store.report_payload(7, old_id)["partner_name"] == "Старый"
    assert store.get_profile(7)["partner_name"] == "Новый"


def test_profile_webapp_marks_partner_name_optional() -> None:
    assert "Имя партнёра <span class=\"optional\">(необязательно)</span>" in webapp.WEBAPP_HTML
    assert "Для разбора мужчины достаточно даты рождения" in webapp.WEBAPP_HTML
    assert "Заполните минимум имя и дату партнёра" not in webapp.WEBAPP_HTML
