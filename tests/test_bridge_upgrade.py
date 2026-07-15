from __future__ import annotations

from app.astro.bridge_upgrade import (
    format_couple_moon_bridge,
    format_couple_moon_bridge_short_card,
)
from app.astro.report import PartnerReport


def _report(name: str, *, sign_key: str, sign_ru: str, element: str, element_ru: str) -> PartnerReport:
    return PartnerReport(
        partner_name=name,
        birth_date="01.01.1990",
        moon_status="stable",
        emotional_language=element,
        emotional_language_title=element_ru,
        placements={
            "moon": {
                "sign_key": sign_key,
                "sign_ru": sign_ru,
                "element": element,
                "element_ru": element_ru,
                "is_retrograde": False,
                "motion_status": "stable",
            }
        },
        summary="",
        text="",
        message_templates=[],
    )


def test_short_bridge_gives_needs_conflict_and_ready_phrase() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="scorpio", sign_ru="Скорпион", element="water", element_ru="Вода")

    text = format_couple_moon_bridge_short_card(man, woman)

    assert "Ему: спокойствие, предсказуемость" in text
    assert "Вам: эмоциональную безопасность" in text
    assert "Где обычно заклинивает" in text
    assert "пятнадцать минут поговорим" in text
    assert "один конкретный следующий шаг" in text


def test_full_bridge_contains_actionable_relationship_protocol() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="scorpio", sign_ru="Скорпион", element="water", element_ru="Вода")

    text = format_couple_moon_bridge(man, woman)

    assert "Ваш вероятный цикл напряжения" in text
    assert "Перевод с поведения на потребность" in text
    assert "Три готовых сценария" in text
    assert "Проверка через 24 часа" in text
    assert "Мост, который строит только один человек" in text
    assert "проблема уже не в Луне" in text
