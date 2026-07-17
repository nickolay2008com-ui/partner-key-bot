from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import app.entertaining_flow as entertaining_flow
import app.storage as storage
import app.webapp as webapp
import app.woman_flow as base
from app import payments
from app.astro import entertaining_blocks as fun

_INSTALLED = False

_ORIGINAL_STORE_ADD = storage.ReportsStore.add
_ORIGINAL_STORE_LATEST = storage.ReportsStore.latest_report_payload
_ORIGINAL_OPEN_HISTORY_REPORT = base.open_history_report
_ORIGINAL_PRODUCT_DETAIL = base.product_detail
_ORIGINAL_DETAIL_TEXT = webapp._detail_text
_ORIGINAL_DETAIL_CARD_KEYBOARD = base.detail_card_keyboard
_ACTIVE_SCHEMA_KEYS: set[tuple[str, str]] = set()

_PLANET_PRODUCT_BY_BLOCK = {
    "venus": "planet_venus",
    "mercury": "planet_mercury",
    "mars": "planet_mars",
    "jupiter": "planet_jupiter",
}

_PAIR_TOPIC_TITLES = {
    "venus": "💗 Симпатия и нежность в вашей паре",
    "mercury": "🗣 Как вам легче разговаривать друг с другом",
    "mars": "🔥 Инициатива и действие в вашей паре",
    "jupiter": "🪐 Смысл и направление роста вашей пары",
}

_DETAIL_LABELS = {
    "moon": "🌙 Эмоциональный ритм мужчины",
    "moon_deep": "🌙 Эмоциональный ритм мужчины глубже",
    "venus": _PAIR_TOPIC_TITLES["venus"],
    "mercury": _PAIR_TOPIC_TITLES["mercury"],
    "mars": _PAIR_TOPIC_TITLES["mars"],
    "jupiter": _PAIR_TOPIC_TITLES["jupiter"],
    "portrait": "👤 Сильные стороны и уязвимости пары",
    "full": "📖 Полная карта отношений",
    "bridge": "💞 Полный эмоциональный мост",
    "details": "✨ Подробный разбор мужчины",
}


def _ensure_active_report_table(store: storage.ReportsStore) -> None:
    schema_key = ("postgres", store.database_url) if store.database_url else ("sqlite", str(store.db_path.resolve()))
    if schema_key in _ACTIVE_SCHEMA_KEYS:
        return

    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_partner_reports (
                    user_id BIGINT PRIMARY KEY,
                    report_id BIGINT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
    else:
        with store._connect_sqlite() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS active_partner_reports (
                    user_id INTEGER PRIMARY KEY,
                    report_id INTEGER NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
    _ACTIVE_SCHEMA_KEYS.add(schema_key)


def _write_active_report(store: storage.ReportsStore, user_id: int, report_id: int) -> None:
    _ensure_active_report_table(store)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                """
                INSERT INTO active_partner_reports (user_id, report_id, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    report_id = excluded.report_id,
                    updated_at = excluded.updated_at
                """,
                (user_id, report_id, now),
            )
        return

    with store._connect_sqlite() as conn:
        conn.execute(
            """
            INSERT INTO active_partner_reports (user_id, report_id, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                report_id = excluded.report_id,
                updated_at = excluded.updated_at
            """,
            (user_id, report_id, now),
        )


def _active_report_id(store: storage.ReportsStore, user_id: int) -> int:
    _ensure_active_report_table(store)
    if store.database_url:
        with store._connect_postgres() as conn:
            row = conn.execute(
                "SELECT report_id FROM active_partner_reports WHERE user_id = %s",
                (user_id,),
            ).fetchone()
    else:
        with store._connect_sqlite() as conn:
            row = conn.execute(
                "SELECT report_id FROM active_partner_reports WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    return int(row["report_id"]) if row else 0


def set_active_report(store: storage.ReportsStore, user_id: int, report_id: int) -> bool:
    if report_id <= 0 or store.report_payload(user_id, report_id) is None:
        return False
    _write_active_report(store, user_id, report_id)
    return True


def active_report_payload(store: storage.ReportsStore, user_id: int) -> dict[str, Any] | None:
    report_id = _active_report_id(store, user_id)
    if report_id > 0:
        payload = store.report_payload(user_id, report_id)
        if payload is not None:
            return payload

    payload = _ORIGINAL_STORE_LATEST(store, user_id)
    if isinstance(payload, dict):
        fallback_id = int(payload.get("_storage_report_id") or 0)
        if fallback_id > 0:
            _write_active_report(store, user_id, fallback_id)
    return payload


def store_add_with_active(store: storage.ReportsStore, user_id: int, report: object) -> int:
    report_id = _ORIGINAL_STORE_ADD(store, user_id, report)
    if report_id > 0:
        _write_active_report(store, user_id, report_id)
    return report_id


def latest_report_payload_with_active(
    store: storage.ReportsStore,
    user_id: int,
) -> dict[str, Any] | None:
    return active_report_payload(store, user_id)


async def open_history_report_with_active(update: Any, context: Any) -> None:
    raw_data = update.callback_query.data if update.callback_query else ""
    try:
        selected_report_id = int(raw_data.rsplit(":", 1)[-1])
    except (TypeError, ValueError):
        selected_report_id = 0

    await _ORIGINAL_OPEN_HISTORY_REPORT(update, context)

    user_id = base._user_id(update)
    restored_report_id = base._current_report_id(context)
    if user_id is not None and selected_report_id > 0 and restored_report_id == selected_report_id:
        await asyncio.to_thread(set_active_report, base.get_store(), user_id, selected_report_id)


def relationship_menu_keyboard(report_id: int = 0) -> base.InlineKeyboardMarkup:
    details_product = base.get_product("details")
    message_product = base.get_product("message")
    details_price = f" — {details_product.rubles} ₽" if details_product else ""
    message_price = f" — {message_product.rubles} ₽" if message_product else ""
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton(
                    "💞 Открыть полный эмоциональный мост",
                    web_app=base.detail_webapp_info("bridge", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"✍️ 2 варианта сообщения{message_price}",
                    callback_data=base._callback_with_report("message", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"📖 Полная карта отношений{details_price}",
                    callback_data=base._callback_with_report("p:full", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    "🪐 Выбрать отдельную тему — 50 ₽",
                    callback_data=base._callback_with_report("premium:planets", report_id),
                )
            ],
            [base.InlineKeyboardButton("🔄 Новый разбор", callback_data="start_man")],
        ]
    )


def detail_card_keyboard(
    block: str,
    locked: bool = False,
    report_id: int = 0,
) -> base.InlineKeyboardMarkup:
    if locked:
        return _ORIGINAL_DETAIL_CARD_KEYBOARD(block, locked=True, report_id=report_id)

    labels = {
        "moon": "🌙 Открыть разбор Луны",
        "moon_deep": "🌙 Открыть глубокий разбор Луны",
        "venus": "💗 Открыть тему симпатии пары",
        "mercury": "🗣 Открыть тему разговора пары",
        "mars": "🔥 Открыть тему инициативы пары",
        "jupiter": "🪐 Открыть тему роста пары",
        "portrait": "👤 Открыть портреты пары",
        "full": "📖 Открыть полную карту отношений",
        "bridge": "💞 Открыть полный эмоциональный мост",
        "details": "✨ Открыть подробный разбор",
    }
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton(
                    labels.get(block, "✨ Открыть подробности"),
                    web_app=base.detail_webapp_info(block, report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    "← К выбору",
                    callback_data=base._callback_with_report("premium:back", report_id),
                )
            ],
        ]
    )


def _has_block_access(
    store: storage.ReportsStore,
    user_id: int,
    report_id: int,
    product_key: str,
) -> bool:
    if store.has_entitlement(user_id, product_key, report_id):
        return True
    return product_key in _PLANET_PRODUCT_BY_BLOCK.values() and store.has_entitlement(
        user_id,
        "details",
        report_id,
    )


async def has_premium_access_with_full_map(
    update: Any,
    context: Any,
    product_key: str,
    report_id: int,
) -> bool:
    user_id = base._user_id(update)
    if user_id is None or report_id <= 0:
        return False
    return await asyncio.to_thread(
        _has_block_access,
        base.get_store(),
        user_id,
        report_id,
        product_key,
    )


def _woman_report(store: storage.ReportsStore, user_id: int) -> base.PartnerReport:
    profile = store.get_profile(user_id)
    birth_date_text = str(profile.get("self_birth_date") or "").strip()
    if not birth_date_text:
        raise ValueError("Для раздела пары сначала добавьте свою дату рождения в Telegram.")
    birth_date = base.parse_birth_date(birth_date_text)
    chart = base.calculate_partner_chart(birth_date)
    return base.build_partner_report(chart, profile.get("self_name") or "вы")


def _format_pair_topic(
    man_report: base.PartnerReport,
    woman_report: base.PartnerReport,
    block: str,
) -> str:
    section = fun._pair_planet_section(man_report, woman_report, block, 1)
    _, separator, body = section.partition("\n")
    clean_body = body.strip() if separator else section
    return f"{_PAIR_TOPIC_TITLES[block]}\n\n{clean_body}"


def _required_product(block: str) -> str | None:
    if block in {"full", "portrait", "details"}:
        return "details"
    return _PLANET_PRODUCT_BY_BLOCK.get(block)


def detail_text_with_contract(user_id: int, block: str, report_id: int = 0) -> str:
    normalized = webapp._normalize_detail_block(block)
    store = webapp.get_store()
    payload = store.report_payload(user_id, report_id) if report_id > 0 else store.latest_report_payload(user_id)
    if not isinstance(payload, dict):
        raise ValueError("Сначала соберите разбор в Telegram.")

    report_id = int(payload.get("_storage_report_id") or 0)
    required_product = _required_product(normalized)
    if required_product and not _has_block_access(
        store,
        user_id,
        report_id,
        required_product,
    ):
        if required_product == "details":
            raise ValueError(
                "Этот раздел входит в полную карту отношений. Вернитесь в Telegram и откройте её после оплаты."
            )
        raise ValueError(
            "Этот раздел открывается после покупки выбранной темы или полной карты отношений. Вернитесь в Telegram."
        )

    if normalized in _PLANET_PRODUCT_BY_BLOCK:
        man_report = webapp._report_from_payload(payload)
        if man_report is None:
            raise ValueError("Не удалось восстановить выбранный разбор. Откройте его заново в Telegram.")
        return _format_pair_topic(man_report, _woman_report(store, user_id), normalized)

    return _ORIGINAL_DETAIL_TEXT(user_id, normalized, report_id)


async def product_detail_with_direct_bridge(update: Any, context: Any) -> None:
    raw_data = update.callback_query.data if update.callback_query else ""
    raw_code, requested_report_id = base._callback_report(raw_data)
    if requested_report_id:
        if not await base._activate_report_context(update, context, requested_report_id):
            await base._tracked_reply_text(
                update,
                context,
                "Эта кнопка относится к недоступному разбору. Откройте нужную карту через историю.",
                reply_markup=base.menu(),
            )
            return
        user_id = base._user_id(update)
        if user_id is not None:
            await asyncio.to_thread(set_active_report, base.get_store(), user_id, requested_report_id)
    legacy_code_map = {
        "v2:couple_moon": "bridge",
        "v2:venus": "venus",
        "v2:mercury": "mercury",
        "v2:mars": "mars",
        "v2:full_report": "full",
    }
    code = legacy_code_map.get(raw_code, raw_code.replace("p:", ""))

    if code == "full":
        report_id = base._current_report_id(context)
        if not await base._has_premium_access(update, context, "details", report_id):
            await _ORIGINAL_PRODUCT_DETAIL(update, context)
            return

    if code in _PLANET_PRODUCT_BY_BLOCK:
        report_id = base._current_report_id(context)
        product_key = _PLANET_PRODUCT_BY_BLOCK[code]
        if not await base._has_premium_access(update, context, product_key, report_id):
            await _ORIGINAL_PRODUCT_DETAIL(update, context)
            return

    if code not in {"bridge", "full", *_PLANET_PRODUCT_BY_BLOCK.keys()}:
        await _ORIGINAL_PRODUCT_DETAIL(update, context)
        return

    if update.callback_query:
        await update.callback_query.answer()
    await base._remember_user(update)
    await base._track_event(update, "product_block_opened", block=code, source=raw_code)
    await base._delete_callback_menu_message(update, context)

    man_report = await base._load_latest_man_report(update, context)
    woman_report = base._load_report(context, base.LAST_WOMAN_REPORT)
    if man_report is None:
        await base._tracked_reply_text(update, context, base._state_lost_text(), reply_markup=base.menu())
        return
    if woman_report is None:
        await base._tracked_reply_text(
            update,
            context,
            "Чтобы открыть раздел пары, сначала добавьте свою дату рождения.",
            reply_markup=base.after_free_keyboard(),
        )
        return

    if code == "bridge":
        text = (
            "💞 Полный эмоциональный мост готов.\n\n"
            "Внутри: ритм каждого, возможные недопонимания, подходящая фраза "
            "и один совместный ритуал."
        )
    elif code == "full":
        text = (
            "📖 Полная карта отношений готова.\n\n"
            "Внутри соединены пять уровней пары: эмоции, симпатия, разговор, "
            "инициатива и направление роста."
        )
    else:
        text = (
            f"{_PAIR_TOPIC_TITLES[code]}\n\n"
            "Парный разбор готов: внутри его сценарий, ваш сценарий, точные знаки "
            "и один совместный эксперимент."
        )

    await base._tracked_reply_text(
        update,
        context,
        text,
        reply_markup=detail_card_keyboard(code, report_id=base._current_report_id(context)),
    )


def _align_payment_products() -> None:
    details = payments.PRODUCTS["details"]
    payments.PRODUCTS["details"] = payments.Product(
        key=details.key,
        title="Полная карта отношений",
        description=(
            "Связная карта пяти уровней пары: эмоции, симпатия, разговор, инициатива и рост, "
            "с практическими шагами для отношений."
        ),
        stars=details.stars,
        rubles=details.rubles,
    )

    message = payments.PRODUCTS["message"]
    payments.PRODUCTS["message"] = payments.Product(
        key=message.key,
        title="2 варианта сообщения",
        description=(
            "Два готовых сообщения, подходящая тональность и стоп-фразы, чтобы начать разговор яснее и бережнее."
        ),
        stars=message.stars,
        rubles=message.rubles,
    )


def _align_webapp_copy() -> None:
    webapp.DETAIL_LABELS.update(_DETAIL_LABELS)

    html = webapp.DETAIL_WEBAPP_HTML
    for version in ("v2", "v3", "v4", "v5", "v6"):
        html = html.replace(
            f"partner-key-detail:${{block}}:{version}",
            "partner-key-detail:${block}:v7",
        )
    html = html.replace(
        "🎬 Астро Партнёр: новая серия",
        "💞 Астро Партнёр",
    ).replace(
        "Здесь планеты становятся героями понятной истории: узнаваемые сцены, лёгкая ирония и один эксперимент, который можно проверить в жизни.",
        "Здесь открыт выбранный раздел вашей карты: ритм каждого, практическая подсказка и признаки, которые можно проверить в жизни.",
    )
    webapp.DETAIL_WEBAPP_HTML = html


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    storage.ReportsStore.add = store_add_with_active
    storage.ReportsStore.latest_report_payload = latest_report_payload_with_active

    base.open_history_report = open_history_report_with_active
    base._has_premium_access = has_premium_access_with_full_map
    base.product_detail = product_detail_with_direct_bridge
    base.detail_card_keyboard = detail_card_keyboard
    base.read_menu_keyboard = relationship_menu_keyboard

    entertaining_flow._relationship_menu_keyboard = relationship_menu_keyboard

    webapp._detail_text = detail_text_with_contract

    _align_payment_products()
    _align_webapp_copy()

    _INSTALLED = True
    base.logger.info("BUTTON_CONTRACTS: button destinations, active reports and paid detail access installed")
