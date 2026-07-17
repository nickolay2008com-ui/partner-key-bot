from __future__ import annotations

from app import button_contracts
from app.astro.report import PartnerReport
from app.storage import ReportsStore


def _report(name: str, birth_date: str = "1993-04-12") -> PartnerReport:
    placements = {
        "moon": {
            "sign_key": "taurus",
            "sign_ru": "Телец",
            "element": "earth",
            "element_ru": "Земля",
            "is_retrograde": False,
        },
        "venus": {
            "sign_key": "gemini",
            "sign_ru": "Близнецы",
            "element": "air",
            "element_ru": "Воздух",
            "is_retrograde": False,
        },
        "mercury": {
            "sign_key": "taurus",
            "sign_ru": "Телец",
            "element": "earth",
            "element_ru": "Земля",
            "is_retrograde": False,
        },
        "mars": {
            "sign_key": "aries",
            "sign_ru": "Овен",
            "element": "fire",
            "element_ru": "Огонь",
            "is_retrograde": False,
        },
        "jupiter": {
            "sign_key": "cancer",
            "sign_ru": "Рак",
            "element": "water",
            "element_ru": "Вода",
            "is_retrograde": False,
        },
    }
    return PartnerReport(
        partner_name=name,
        birth_date=birth_date,
        moon_status="exact",
        emotional_language="earth",
        emotional_language_title="Земля",
        placements=placements,
        summary="",
        text="",
        message_templates=[],
    )


def test_relationship_menu_opens_full_bridge_directly() -> None:
    keyboard = button_contracts.relationship_menu_keyboard()
    first_button = keyboard.inline_keyboard[0][0]

    assert first_button.text == "💞 Открыть полный эмоциональный мост"
    assert first_button.callback_data is None
    assert first_button.web_app is not None
    assert first_button.web_app.url.endswith("/webapp/detail/bridge")

    callbacks = [
        button.callback_data
        for row in keyboard.inline_keyboard[1:]
        for button in row
    ]
    assert callbacks == ["message", "p:full", "premium:planets", "start_man"]


def test_selected_history_report_becomes_the_webapp_report(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    first_id = button_contracts._ORIGINAL_STORE_ADD(store, 101, _report("Первый"))
    second_id = button_contracts._ORIGINAL_STORE_ADD(store, 101, _report("Второй"))

    assert second_id > first_id
    assert button_contracts.set_active_report(store, 101, first_id) is True

    payload = button_contracts.latest_report_payload_with_active(store, 101)

    assert payload is not None
    assert payload["partner_name"] == "Первый"
    assert payload["_storage_report_id"] == first_id


def test_full_map_purchase_unlocks_individual_topics(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = button_contracts._ORIGINAL_STORE_ADD(store, 101, _report("Андрей"))
    store.grant_entitlement(101, "details", report_id, "payment-full")

    assert button_contracts._has_block_access(store, 101, report_id, "planet_venus") is True
    assert button_contracts._has_block_access(store, 101, report_id, "planet_mercury") is True
    assert button_contracts._has_block_access(store, 101, report_id, "planet_mars") is True
    assert button_contracts._has_block_access(store, 101, report_id, "planet_jupiter") is True


def test_single_topic_purchase_does_not_unlock_other_topics(tmp_path) -> None:
    store = ReportsStore(tmp_path / "reports.sqlite3")
    report_id = button_contracts._ORIGINAL_STORE_ADD(store, 101, _report("Андрей"))
    store.grant_entitlement(101, "planet_venus", report_id, "payment-venus")

    assert button_contracts._has_block_access(store, 101, report_id, "planet_venus") is True
    assert button_contracts._has_block_access(store, 101, report_id, "planet_mars") is False


def test_paid_topic_content_compares_both_people() -> None:
    text = button_contracts._format_pair_topic(
        _report("Андрей"),
        _report("Анна", "1994-05-13"),
        "venus",
    )

    assert text.startswith("💗 Симпатия и нежность в вашей паре")
    assert "Он:" in text
    assert "Вы:" in text
    assert "Совместный эксперимент" in text


def test_current_detail_labels_match_button_promises() -> None:
    assert button_contracts._DETAIL_LABELS["bridge"] == "💞 Полный эмоциональный мост"
    assert button_contracts._DETAIL_LABELS["full"] == "📖 Полная карта отношений"
    assert button_contracts._DETAIL_LABELS["venus"] == "💗 Симпатия и нежность в вашей паре"
