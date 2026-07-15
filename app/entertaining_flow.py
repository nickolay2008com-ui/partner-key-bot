from __future__ import annotations

import app.partner_flow as current
import app.webapp as webapp
import app.woman_flow as base
from app.astro import entertaining_blocks as fun


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
webapp.format_couple_portraits = fun.format_couple_portraits
webapp.format_couple_full_report = fun.format_couple_full_report
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
