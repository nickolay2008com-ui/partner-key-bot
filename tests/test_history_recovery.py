from app.astro.report import PartnerReport
from app.storage import ReportsStore
from app.woman_flow import history_keyboard


def _report(name: str, birth_date: str) -> PartnerReport:
    return PartnerReport(
        partner_name=name,
        birth_date=birth_date,
        moon_status="exact",
        emotional_language="earth",
        emotional_language_title="Язык спокойствия",
        placements={},
        summary="test",
        text="test",
        message_templates=[],
    )


def test_report_payload_only_returns_report_owned_by_user(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    first_id = store.add(101, _report("Первый", "1990-01-01"))
    second_id = store.add(101, _report("Второй", "1991-02-02"))

    restored = store.report_payload(101, first_id)

    assert restored is not None
    assert restored["partner_name"] == "Первый"
    assert restored["_storage_report_id"] == first_id
    assert store.report_payload(101, second_id) is not None
    assert store.report_payload(202, first_id) is None


def test_history_keyboard_opens_specific_saved_report(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(101, _report("Андрей", "1990-01-01"))

    keyboard = history_keyboard(store.recent(101))

    assert keyboard.inline_keyboard[0][0].text == "💞 Андрей, 1990-01-01"
    assert keyboard.inline_keyboard[0][0].callback_data == f"history:open:{report_id}"


def test_has_any_entitlement_is_scoped_to_user_and_report(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = store.add(101, _report("Андрей", "1990-01-01"))
    store.grant_entitlement(101, "details", report_id, "payment-1")

    assert store.has_any_entitlement(101, report_id) is True
    assert store.has_any_entitlement(202, report_id) is False
    assert store.has_any_entitlement(101, report_id + 1) is False
