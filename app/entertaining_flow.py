from __future__ import annotations

import app.partner_flow as current
import app.webapp as webapp
import app.woman_flow as base
from app.astro import entertaining_blocks as fun


def _fix_pair_you_lines(text: str) -> str:
    replacements = {
        "Вы: Его чувства": "Вы: Ваши чувства",
        "Вы: Его Венера": "Вы: Ваша Венера",
        "Вы: Он мыслит": "Вы мыслите",
        "Вы: Он слышит": "Вы слышите",
        "Вы: Его Марс": "Вы: Ваш Марс",
        "Вы: Он растёт": "Вы растёте",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _fix_woman_portrait(text: str, woman_name: str) -> str:
    marker = f"👤 {woman_name}: ваша роль в отношениях"
    if marker not in text:
        return text
    before, after = text.split(marker, 1)
    replacements = {
        "Его чувства": "Ваши чувства",
        "Его Венера": "Ваша Венера",
        "Он мыслит": "Вы мыслите",
        "Он слышит": "Вы слышите",
        "Его Марс": "Ваш Марс",
        "Он растёт": "Вы растёте",
        "Что для него выглядит как любовь": "Что для вас выглядит как любовь",
        "Как устроен его переводчик": "Как устроен ваш переводчик",
        "Ради какого будущего он оживает": "Ради какого будущего вы оживаете",
    }
    for source, target in replacements.items():
        after = after.replace(source, target)
    return before + marker + after


def _couple_portraits(man_report, woman_report):
    return _fix_woman_portrait(fun.format_couple_portraits(man_report, woman_report), woman_report.partner_name)


def _couple_full_report(man_report, woman_report):
    return _fix_pair_you_lines(fun.format_couple_full_report(man_report, woman_report))


# Telegram cards use function references imported by woman_flow, while the WebApp
# keeps its own imported references. Patch both namespaces and leave calculations,
# storage and payments untouched.
base.format_planet_short_card = fun.format_planet_short_card
base.format_couple_moon_bridge_short_card = fun.format_couple_moon_bridge_short_card
base.format_couple_portraits_short_card = fun.format_couple_portraits_short_card

webapp.format_moon_detail = fun.format_moon_detail
webapp.format_moon_deep_detail = fun.format_moon_deep_detail
webapp.format_venus_detail = fun.format_venus_detail
webapp.format_mercury_detail = fun.format_mercury_detail
webapp.format_mars_detail = fun.format_mars_detail
webapp.format_jupiter_detail = fun.format_jupiter_detail
webapp.format_couple_moon_bridge = fun.format_couple_moon_bridge
webapp.format_couple_portraits = _couple_portraits
webapp.format_couple_full_report = _couple_full_report
webapp.format_moon_variant_cards = fun.format_moon_variant_cards
webapp.DETAIL_LABELS.update(fun.DETAIL_LABELS)

_original_detail_text = webapp._detail_text


def _entertaining_detail_text(user_id: int, block: str) -> str:
    normalized = webapp._normalize_detail_block(block)
    if normalized == "details":
        report = webapp._report_from_payload(webapp.get_store().latest_report_payload(user_id))
        if report is None:
            raise ValueError("Сначала соберите разбор в боте — тогда здесь откроется история героя.")
        return fun.format_person_full_story(report)
    return _original_detail_text(user_id, normalized)


webapp._detail_text = _entertaining_detail_text
webapp.DETAIL_WEBAPP_HTML = (
    webapp.DETAIL_WEBAPP_HTML.replace(
        "partner-key-detail:${block}:v2",
        "partner-key-detail:${block}:v3",
    )
    .replace(
        "✨ Инструкция к любимому мужчине",
        "🎬 Астро Партнёр: новая серия",
    )
    .replace(
        "Это не сухой прогноз, а мягкая инструкция: какие слова, внимание и действия помогают ему раскрыться рядом с вами.",
        "Здесь планеты становятся героями понятной истории: узнаваемые сцены, лёгкая ирония и один эксперимент, который можно проверить в жизни.",
    )
)


def main() -> None:
    base.logger.info("BOT_BOOT: starting entertaining partner readings")
    current.main()


if __name__ == "__main__":
    main()
