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


def test_short_bridge_describes_real_conflict_and_next_action() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="scorpio", sign_ru="Скорпион", element="water", element_ru="Вода")

    text = format_couple_moon_bridge_short_card(man, woman)

    assert "Что помогает ему не закрываться" in text
    assert "что будет дальше" in text
    assert "не формальные слова" in text
    assert "замолкает" in text
    assert "Фраза, которую реально можно сказать" in text
    assert "когда мы спокойно к этому вернёмся" in text
    assert "назвал ли он время разговора" in text
    assert "на что мы можем опереться" not in text


def test_full_bridge_uses_plain_language_and_realistic_checks() -> None:
    man = _report("Он", sign_key="taurus", sign_ru="Телец", element="earth", element_ru="Земля")
    woman = _report("Вы", sign_key="scorpio", sign_ru="Скорпион", element="water", element_ru="Вода")

    text = format_couple_moon_bridge(man, woman)

    assert "Как раскручивается ссора" in text
    assert "Что вы можете ошибочно прочитать" in text
    assert "один эпизод, а не всю историю отношений" in text
    assert "Три нормальные фразы" in text
    assert "Как проверить, что это не просто красивый текст" in text
    assert "слова подтверждаются действием" in text
    assert "проблема не в Луне" in text
    assert "сделать эту ситуацию безопаснее" not in text
