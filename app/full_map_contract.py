from __future__ import annotations

from typing import Any, Callable

import app.entertaining_flow as entertaining_flow
import app.webapp as webapp
import app.woman_flow as base

_INSTALLED = False


def _load_pair(user_id: int) -> tuple[base.PartnerReport, base.PartnerReport]:
    store = webapp.get_store()
    payload = store.latest_report_payload(user_id)
    man_report = webapp._report_from_payload(payload)
    if man_report is None:
        raise ValueError("Сначала соберите разбор в Telegram.")

    profile = store.get_profile(user_id)
    birth_date_text = str(profile.get("self_birth_date") or "").strip()
    if not birth_date_text:
        raise ValueError("Для полной карты пары сначала добавьте свою дату рождения в Telegram.")

    birth_date = base.parse_birth_date(birth_date_text)
    chart = base.calculate_partner_chart(birth_date)
    woman_report = base.build_partner_report(chart, profile.get("self_name") or "вы")
    return man_report, woman_report


def build_detail_router(original: Callable[[int, str], str]) -> Callable[[int, str], str]:
    """Keep the bridge and the full five-planet map on explicit separate routes."""

    def routed(user_id: int, block: str) -> str:
        normalized = webapp._normalize_detail_block(block)
        if normalized == "full":
            man_report, woman_report = _load_pair(user_id)
            return entertaining_flow._couple_full_report(man_report, woman_report)
        if normalized == "bridge":
            man_report, woman_report = _load_pair(user_id)
            return webapp.format_couple_moon_bridge(
                man_report,
                woman_report,
                include_transition_variants=False,
            )
        return original(user_id, normalized)

    return routed


def _bump_detail_cache() -> None:
    html = webapp.DETAIL_WEBAPP_HTML
    for version in ("v2", "v3", "v4", "v5", "v6", "v7", "v8"):
        html = html.replace(
            f"partner-key-detail:${{block}}:{version}",
            "partner-key-detail:${block}:v9",
        )
    webapp.DETAIL_WEBAPP_HTML = html


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    webapp._detail_text = build_detail_router(webapp._detail_text)
    _bump_detail_cache()

    _INSTALLED = True
    base.logger.info("FULL_MAP_CONTRACT: full map and emotional bridge routed separately")
