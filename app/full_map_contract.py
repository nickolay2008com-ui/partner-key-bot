from __future__ import annotations

from typing import Callable

import app.button_contracts as contracts
import app.entertaining_flow as entertaining_flow
import app.webapp as webapp
import app.woman_flow as base

_INSTALLED = False


def _load_pair(
    user_id: int,
    *,
    report_id: int = 0,
    require_full_access: bool = False,
) -> tuple[base.PartnerReport, base.PartnerReport]:
    store = webapp.get_store()
    payload = store.report_payload(user_id, report_id) if report_id > 0 else store.latest_report_payload(user_id)
    if not isinstance(payload, dict):
        raise ValueError("Сначала соберите разбор в Telegram.")

    report_id = int(payload.get("_storage_report_id") or 0)
    if require_full_access and (
        report_id <= 0 or not contracts._has_block_access(store, user_id, report_id, "details")
    ):
        raise ValueError(
            "Полная карта отношений открывается после оплаты. Вернитесь в Telegram и откройте её из текущего разбора."
        )

    man_report = webapp._report_from_payload(payload)
    if man_report is None:
        raise ValueError("Не удалось восстановить выбранный разбор. Откройте его заново в Telegram.")

    profile = store.get_profile(user_id)
    birth_date_text = str(profile.get("self_birth_date") or "").strip()
    if not birth_date_text:
        raise ValueError("Для полной карты пары сначала добавьте свою дату рождения в Telegram.")

    birth_date = base.parse_birth_date(birth_date_text)
    chart = base.calculate_partner_chart(birth_date)
    woman_report = base.build_partner_report(chart, profile.get("self_name") or "вы")
    return man_report, woman_report


def build_detail_router(original: Callable[[int, str, int], str]) -> Callable[[int, str, int], str]:
    """Keep the bridge and the paid five-planet map on explicit separate routes."""

    def routed(user_id: int, block: str, report_id: int = 0) -> str:
        normalized = webapp._normalize_detail_block(block)
        if normalized == "full":
            man_report, woman_report = _load_pair(
                user_id,
                report_id=report_id,
                require_full_access=True,
            )
            return entertaining_flow._couple_full_report(man_report, woman_report)
        if normalized == "bridge":
            man_report, woman_report = _load_pair(user_id, report_id=report_id)
            return webapp.format_couple_moon_bridge(
                man_report,
                woman_report,
                include_transition_variants=False,
            )
        return original(user_id, normalized, report_id)

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
    base.logger.info("FULL_MAP_CONTRACT: paid full map and free emotional bridge routed separately")
