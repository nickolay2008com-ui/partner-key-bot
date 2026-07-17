from __future__ import annotations

from copy import deepcopy

from app.astro.relationship_map import build_couple_full_map_view
from app.astro.report import PartnerReport
from app.webapp import DETAIL_WEBAPP_HTML


def _report(name: str, signs: dict[str, tuple[str, str, str, str]]) -> PartnerReport:
    placements = {
        planet: {
            "sign_key": sign_key,
            "sign_ru": sign_ru,
            "element": element,
            "element_ru": element_ru,
            "is_retrograde": False,
            "motion_status": "stable",
        }
        for planet, (sign_key, sign_ru, element, element_ru) in signs.items()
    }
    return PartnerReport(
        partner_name=name,
        birth_date="1990-01-01",
        moon_status="stable",
        emotional_language=placements["moon"]["element"],
        emotional_language_title=placements["moon"]["element_ru"],
        placements=placements,
        summary="",
        text="",
        message_templates=[],
    )


def _pair() -> tuple[PartnerReport, PartnerReport]:
    man = _report(
        "Алексей",
        {
            "moon": ("capricorn", "Козерог", "earth", "Земля"),
            "venus": ("aries", "Овен", "fire", "Огонь"),
            "mercury": ("pisces", "Рыбы", "water", "Вода"),
            "mars": ("cancer", "Рак", "water", "Вода"),
            "jupiter": ("libra", "Весы", "air", "Воздух"),
        },
    )
    woman = _report(
        "Мария",
        {
            "moon": ("cancer", "Рак", "water", "Вода"),
            "venus": ("cancer", "Рак", "water", "Вода"),
            "mercury": ("cancer", "Рак", "water", "Вода"),
            "mars": ("libra", "Весы", "air", "Воздух"),
            "jupiter": ("sagittarius", "Стрелец", "fire", "Огонь"),
        },
    )
    return man, woman


def test_full_map_is_a_five_layer_strategy_instead_of_repeated_portraits() -> None:
    man, woman = _pair()

    view = build_couple_full_map_view(man, woman)

    assert view["title"] == "Алексей + Мария: стратегия вашей пары"
    assert [layer["key"] for layer in view["layers"]] == ["moon", "venus", "mercury", "mars", "jupiter"]
    assert view["layers"][1]["formula"] == "Его Венера: Овен · Огонь · Ваша Венера: Рак · Вода"
    assert view["layers"][3]["formula"] == "Его Марс: Рак · Вода · Ваш Марс: Весы · Воздух"
    assert all(layer["resource"] and layer["friction"] for layer in view["layers"])
    assert all(layer["phrase"] and layer["action"] and layer["success"] for layer in view["layers"])
    assert len(view["week_plan"]) == 7


def test_full_map_uses_existing_placements_without_mutating_mechanics() -> None:
    man, woman = _pair()
    man_before = deepcopy(man.to_dict())
    woman_before = deepcopy(woman.to_dict())

    view = build_couple_full_map_view(man, woman)

    assert man.to_dict() == man_before
    assert woman.to_dict() == woman_before
    assert view["layers"][2]["sides"][0]["exact"].startswith("Меркурий в Рыбах")
    assert view["layers"][2]["sides"][1]["exact"].startswith("Меркурий в Раке")


def test_full_map_supports_every_element_pair_on_every_planet() -> None:
    signs = {
        "fire": ("aries", "Овен", "fire", "Огонь"),
        "earth": ("taurus", "Телец", "earth", "Земля"),
        "air": ("gemini", "Близнецы", "air", "Воздух"),
        "water": ("cancer", "Рак", "water", "Вода"),
    }

    for man_element, man_sign in signs.items():
        for woman_element, woman_sign in signs.items():
            man = _report("Он", {planet: man_sign for planet in ("moon", "venus", "mercury", "mars", "jupiter")})
            woman = _report("Вы", {planet: woman_sign for planet in ("moon", "venus", "mercury", "mars", "jupiter")})
            view = build_couple_full_map_view(man, woman)
            assert len(view["layers"]) == 5, (man_element, woman_element)
            assert all(layer["resource"] and layer["friction"] for layer in view["layers"])


def test_full_map_keeps_astrology_honest_and_actionable() -> None:
    man, woman = _pair()

    view = build_couple_full_map_view(man, woman)

    assert "карта предлагает гипотезы" in view["method"]["body"]
    assert "не заменяет разговор, границы и реальные поступки" in view["method"]["body"]
    assert [item["label"] for item in view["summary"]] == ["Опора", "Перевод", "Движение"]
    assert view["week_plan"][-1]["title"] == "Сверка"


def test_full_map_html_uses_cards_accordions_and_copyable_phrases() -> None:
    assert 'class="full-map-view"' in DETAIL_WEBAPP_HTML
    assert "function renderFullMap(model)" in DETAIL_WEBAPP_HTML
    assert "function renderPlanetLayer(layer, index)" in DETAIL_WEBAPP_HTML
    assert "details.open = index === 0" in DETAIL_WEBAPP_HTML
    assert "Скопировать фразу" in DETAIL_WEBAPP_HTML
    assert "if (block === 'full' && data.fullMap) renderFullMap(data.fullMap)" in DETAIL_WEBAPP_HTML
    assert "partner-key-detail:${reportId}:${block}:v12" in DETAIL_WEBAPP_HTML
