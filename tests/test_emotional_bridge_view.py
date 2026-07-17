from __future__ import annotations

from dataclasses import replace

from app.astro.emotional_bridge import build_couple_moon_bridge_view
from app.astro.report import PartnerReport
from app.webapp import DETAIL_WEBAPP_HTML


def _report(name: str, sign_key: str, sign_ru: str, element: str, element_ru: str) -> PartnerReport:
    moon = {
        "sign_key": sign_key,
        "sign_ru": sign_ru,
        "element": element,
        "element_ru": element_ru,
        "is_retrograde": False,
    }
    return PartnerReport(
        partner_name=name,
        birth_date="1990-01-01",
        moon_status="stable",
        emotional_language=element,
        emotional_language_title=element_ru,
        placements={"moon": moon},
        summary="",
        text="",
        message_templates=[],
    )


def test_bridge_view_turns_existing_moon_data_into_a_two_sided_route() -> None:
    man = _report("Андрей", "aries", "Овен", "fire", "Огонь")
    woman = _report("Анна", "cancer", "Рак", "water", "Вода")

    view = build_couple_moon_bridge_view(man, woman)

    assert view["title"] == "Андрей + Анна: как возвращаться друг к другу"
    assert view["formula"] == [
        {"label": "Андрей", "value": "Луна в Овне", "element": "Огонь"},
        {"label": "Анна", "value": "Луна в Раке", "element": "Вода"},
    ]
    assert view["insight"]["title"] == "Ваш мост — тепло, которое не торопит глубину"
    assert view["shores"][0]["role"] == "Его берег"
    assert view["shores"][1]["role"] == "Ваш берег"
    assert "дать быстрый живой сигнал" in view["shores"][0]["bridge"]
    assert "сначала дать тепло и безопасность" in view["shores"][1]["bridge"]
    assert "не как проверку любви" in view["protocol"][1]["text"]


def test_bridge_view_has_copywriting_value_and_a_safe_reality_check() -> None:
    view = build_couple_moon_bridge_view(
        _report("Он", "taurus", "Телец", "earth", "Земля"),
        _report("Вы", "aquarius", "Водолей", "air", "Воздух"),
    )

    assert [phrase["label"] for phrase in view["phrases"]] == ["Тёпло", "Ясно", "После паузы"]
    assert view["experiment"]["title"] == "Эксперимент на ближайшие 24 часа"
    assert len(view["experiment"]["steps"]) == 3
    assert len(view["experiment"]["success"]) == 3
    assert "Мост не означает терпеть холод, давление или обесценивание" in view["experiment"]["boundary"]
    assert "рабочая гипотеза" in view["astrology"]["body"]
    assert "Полная карта показывает весь маршрут" in view["next_level"]["title"]


def test_every_element_pair_has_a_specific_bridge_story() -> None:
    signs = {
        "fire": ("aries", "Овен", "Огонь"),
        "earth": ("taurus", "Телец", "Земля"),
        "air": ("gemini", "Близнецы", "Воздух"),
        "water": ("cancer", "Рак", "Вода"),
    }

    headlines = set()
    for man_element, (man_key, man_sign, man_ru) in signs.items():
        for woman_element, (woman_key, woman_sign, woman_ru) in signs.items():
            view = build_couple_moon_bridge_view(
                _report("Он", man_key, man_sign, man_element, man_ru),
                _report("Вы", woman_key, woman_sign, woman_element, woman_ru),
            )
            headlines.add(view["insight"]["title"])
            assert view["translation"]["body"]
            assert view["protocol"][2]["text"]

    assert len(headlines) == 10


def test_bridge_precision_is_honest_when_birth_time_can_change_the_moon() -> None:
    man = _report("Он", "aries", "Овен", "fire", "Огонь")
    woman = _report("Вы", "cancer", "Рак", "water", "Вода")
    man = replace(man, moon_status="changed_during_day")

    view = build_couple_moon_bridge_view(man, woman)

    assert "Луна могла сменить знак" in view["astrology"]["precision"]
    assert "сравнить соседние положения" in view["astrology"]["precision"]


def test_html_bridge_has_semantic_cards_phrase_tabs_and_copy_action() -> None:
    assert 'class="bridge-view"' in DETAIL_WEBAPP_HTML
    assert "function renderBridge(model)" in DETAIL_WEBAPP_HTML
    assert "function renderPhrases(phrases)" in DETAIL_WEBAPP_HTML
    assert "Скопировать фразу" in DETAIL_WEBAPP_HTML
    assert "navigator.clipboard.writeText" in DETAIL_WEBAPP_HTML
    assert "if (block === 'bridge' && data.bridge) renderBridge(data.bridge)" in DETAIL_WEBAPP_HTML
    assert "Структура моста без повторов" not in DETAIL_WEBAPP_HTML
