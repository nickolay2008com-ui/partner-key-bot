from __future__ import annotations

import pytest

from app import full_map_contract
from app.astro.report import PartnerReport


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


def test_full_map_formatter_contains_all_five_planet_levels() -> None:
    text = full_map_contract.entertaining_flow._couple_full_report(
        _report("Андрей"),
        _report("Анна", "1994-05-13"),
    )

    assert "Эпизод 1. Луна" in text
    assert "Эпизод 2. Венера" in text
    assert "Эпизод 3. Меркурий" in text
    assert "Эпизод 4. Марс" in text
    assert "Эпизод 5. Юпитер" in text
    assert "Ваш эмоциональный мост" not in text


def test_full_and_bridge_use_separate_explicit_routes(monkeypatch) -> None:
    pair = (_report("Андрей"), _report("Анна", "1994-05-13"))
    calls: list[tuple[str, bool]] = []

    def fake_load_pair(user_id: int, *, require_full_access: bool = False):
        calls.append((str(user_id), require_full_access))
        return pair

    monkeypatch.setattr(full_map_contract, "_load_pair", fake_load_pair)
    monkeypatch.setattr(
        full_map_contract.entertaining_flow,
        "_couple_full_report",
        lambda man, woman: "FULL FIVE PLANETS",
    )
    monkeypatch.setattr(
        full_map_contract.webapp,
        "format_couple_moon_bridge",
        lambda man, woman, include_transition_variants=False: "EMOTIONAL BRIDGE",
    )

    router = full_map_contract.build_detail_router(lambda user_id, block: f"ORIGINAL {block}")

    assert router(101, "full") == "FULL FIVE PLANETS"
    assert router(101, "bridge") == "EMOTIONAL BRIDGE"
    assert router(101, "venus") == "ORIGINAL venus"
    assert calls == [("101", True), ("101", False)]


def test_full_map_access_is_checked_before_content_is_built(monkeypatch) -> None:
    report = _report("Андрей")
    payload = report.to_dict() | {"_storage_report_id": 77}

    class Store:
        def latest_report_payload(self, user_id: int):
            return payload

        def get_profile(self, user_id: int):
            return {"self_name": "Анна", "self_birth_date": "13.05.1994"}

    monkeypatch.setattr(full_map_contract.webapp, "get_store", lambda: Store())
    monkeypatch.setattr(full_map_contract.contracts, "_has_block_access", lambda *args: False)

    with pytest.raises(ValueError, match="после оплаты"):
        full_map_contract._load_pair(101, require_full_access=True)


def test_detail_cache_version_is_bumped(monkeypatch) -> None:
    monkeypatch.setattr(
        full_map_contract.webapp,
        "DETAIL_WEBAPP_HTML",
        "const cacheKey = `partner-key-detail:${block}:v7`;",
    )

    full_map_contract._bump_detail_cache()

    assert "partner-key-detail:${block}:v9" in full_map_contract.webapp.DETAIL_WEBAPP_HTML
    assert "partner-key-detail:${block}:v7" not in full_map_contract.webapp.DETAIL_WEBAPP_HTML
