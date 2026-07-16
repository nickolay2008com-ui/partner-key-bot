from __future__ import annotations

from app.astro.bridge_upgrade import (
    format_couple_moon_bridge,
    format_couple_moon_bridge_short_card,
    format_relationship_menu_summary,
)
from app.astro.report import PartnerReport


def _report(name: str, *, sign_key: str, sign_ru: str, element: str, element_ru: str) -> PartnerReport:
    placements = {}
    for planet in ("moon", "venus", "mercury", "mars", "jupiter"):
        placements[planet] = {
            "sign_key": sign_key,
            "sign_ru": sign_ru,
            "element": element,
            "element_ru": element_ru,
            "is_retrograde": False,
            "motion_status": "stable",
        }
    return PartnerReport(
        partner_name=name,
        birth_date="01.01.1990",
        moon_status="stable",
        emotional_language=element,
        emotional_language_title=element_ru,
        placements=placements,
        summary="",
        text="",
        message_templates=[],
    )


def test_short_bridge_builds_shared_rhythm_without_problem_framing() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="capricorn", sign_ru="Козерог", element="earth", element_ru="Земля")

    text = format_couple_moon_bridge_short_card(man, woman)

    assert "(Он: Луна в Тельце, Земля · Вы: Луна в Козероге, Земля)" in text
    assert "Ваш общий ритм" in text
    assert "Что особенно хорошо соединяет вас" in text
    assert "Фраза для поддержания близости" in text
    assert "Мягкий шаг" in text
    assert "что будет только нашим" in text
    assert "Ваш общий вклад в связь" in text
    assert "Попробуйте такой ритуал" in text
    assert "Вы сближается" not in text
    assert "вы сам" not in text.lower()
    assert "как вы обычно застреваете" not in text.lower()
    assert "ссора" not in text.lower()


def test_full_bridge_focuses_on_supporting_connection() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="scorpio", sign_ru="Скорпион", element="water", element_ru="Вода")

    text = format_couple_moon_bridge(man, woman)

    assert "Что уже соединяет вас" in text
    assert "Как он чувствует близость" in text
    assert "Как вы чувствуете близость" in text
    assert "Как сочетаются ваши темпы" in text
    assert "Как поддерживать общий ритм" in text
    assert "Подходящий совместный ритуал" in text
    assert "Как понять, что мост работает" in text
    assert "Следующие уровни карты покажут язык любви по Венере" in text
    assert "проблема не в Луне" not in text
    assert "Как раскручивается ссора" not in text


def test_relationship_menu_shows_planet_sign_and_element_after_description() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="scorpio", sign_ru="Скорпион", element="water", element_ru="Вода")

    text = format_relationship_menu_summary(man, woman)

    assert "💞 Эмоциональный мост\nКак вы чувствуете близость" in text
    assert "(Он: Луна в Тельце, Земля · Вы: Луна в Скорпионе, Вода)" in text
    assert "💗 Язык любви\nКак каждый выражает любовь" in text
    assert "(Он: Венера в Тельце, Земля · Вы: Венера в Скорпионе, Вода)" in text
    assert "(Он: Меркурий в Тельце, Земля · Вы: Меркурий в Скорпионе, Вода)" in text
    assert "(Он: Марс в Тельце, Земля · Вы: Марс в Скорпионе, Вода)" in text
    assert "(Он: Юпитер в Тельце, Земля · Вы: Юпитер в Скорпионе, Вода)" in text
