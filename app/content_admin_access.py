from __future__ import annotations

import asyncio
from contextvars import ContextVar
from functools import wraps
from typing import Any, Awaitable, Callable

from telegram.ext import CallbackQueryHandler

import app.woman_flow as base

_INSTALLED = False
_CURRENT_USER_ID: ContextVar[int | None] = ContextVar("content_admin_user_id", default=None)
_ORIGINAL_PREMIUM_KEYBOARD: Callable[..., base.InlineKeyboardMarkup] | None = None

_ADMIN_PRODUCTS = {
    "details",
    "message",
    *base.PAID_PLANET_PRODUCTS.values(),
}


def _is_content_admin_id(user_id: int | None) -> bool:
    return bool(user_id and user_id in getattr(base.settings, "content_admin_ids", set()))


def _admin_unlock_callback(product_key: str, report_id: int) -> str:
    return base._callback_with_report(f"admin:unlock:{product_key}", report_id)


def premium_keyboard_with_admin(
    product_key: str,
    report_id: int = 0,
) -> base.InlineKeyboardMarkup:
    if _ORIGINAL_PREMIUM_KEYBOARD is None:
        raise RuntimeError("Content admin access is not installed")

    markup = _ORIGINAL_PREMIUM_KEYBOARD(product_key, report_id)
    if not _is_content_admin_id(_CURRENT_USER_ID.get()) or product_key not in _ADMIN_PRODUCTS:
        return markup

    rows = [list(row) for row in markup.inline_keyboard]
    rows.insert(
        1,
        [
            base.InlineKeyboardButton(
                "🛠 Админ — открыть",
                callback_data=_admin_unlock_callback(product_key, report_id),
            )
        ],
    )
    return base.InlineKeyboardMarkup(rows)


def _with_admin_context(
    handler: Callable[[Any, Any], Awaitable[Any]],
) -> Callable[[Any, Any], Awaitable[Any]]:
    @wraps(handler)
    async def contextual(update: Any, context: Any) -> Any:
        token = _CURRENT_USER_ID.set(base._user_id(update))
        try:
            return await handler(update, context)
        finally:
            _CURRENT_USER_ID.reset(token)

    return contextual


async def _replace_with_opened_content(
    update: Any,
    context: Any,
    product_key: str,
    report_id: int,
) -> None:
    if product_key == "message":
        report = await base._load_latest_man_report(update, context)
        if report is None:
            await base._tracked_replace_callback_text(
                update,
                context,
                base._state_lost_text(),
                reply_markup=base.menu(),
            )
            return
        await base._tracked_replace_callback_text(
            update,
            context,
            base.format_message_guidance(report),
            reply_markup=base.after_bridge_keyboard(report_id),
        )
        return

    block = base.planet_product_key_to_block(product_key)
    if product_key == "details":
        block = "full"
    if block is None:
        raise ValueError(f"Unsupported admin product: {product_key}")

    labels = {
        "full": "📖 Полная карта отношений",
        "venus": "💗 Секреты любви",
        "mercury": "🗣 Стиль общения",
        "mars": "🔥 Притяжение и инициатива",
        "jupiter": "🪐 Рост пары",
    }
    await base._tracked_replace_callback_text(
        update,
        context,
        f"🛠 Админ-доступ открыт.\n\n{labels[block]} готов к просмотру.",
        reply_markup=base.detail_card_keyboard(block, report_id=report_id),
    )


async def admin_unlock(update: Any, context: Any) -> None:
    query = update.callback_query
    user_id = base._user_id(update)
    if query is None:
        return
    if not _is_content_admin_id(user_id):
        await query.answer("Эта кнопка доступна только администратору.", show_alert=True)
        return

    await query.answer()
    action, requested_report_id = base._callback_report(str(query.data or ""))
    product_key = action.removeprefix("admin:unlock:")
    if product_key not in _ADMIN_PRODUCTS or base.get_product(product_key) is None:
        await base._tracked_replace_callback_text(
            update,
            context,
            "Не удалось определить Premium-раздел. Откройте его заново из текущей карты.",
            reply_markup=base.menu(),
        )
        return

    if requested_report_id and not await base._activate_report_context(
        update,
        context,
        requested_report_id,
    ):
        await base._tracked_replace_callback_text(
            update,
            context,
            "Эта кнопка относится к недоступному разбору. Откройте нужную карту через историю.",
            reply_markup=base.menu(),
        )
        return

    report_id = base._current_report_id(context)
    if user_id is None or report_id <= 0:
        await base._tracked_replace_callback_text(
            update,
            context,
            "Сначала соберите карту пары — админ-доступ привязывается к конкретному разбору.",
            reply_markup=base.menu(),
        )
        return

    await asyncio.to_thread(
        base.get_store().grant_entitlement,
        user_id,
        product_key,
        report_id,
        f"admin:{user_id}",
    )
    await base._track_event(
        update,
        "premium_admin_access_granted",
        product_key=product_key,
        report_id=report_id,
        provider="admin",
    )
    await _replace_with_opened_content(update, context, product_key, report_id)


def install() -> None:
    global _INSTALLED, _ORIGINAL_PREMIUM_KEYBOARD
    if _INSTALLED:
        return

    _ORIGINAL_PREMIUM_KEYBOARD = base.premium_keyboard
    base.premium_keyboard = premium_keyboard_with_admin
    base.premium_offer = _with_admin_context(base.premium_offer)
    base.product_detail = _with_admin_context(base.product_detail)
    base.message_hint = _with_admin_context(base.message_hint)

    original_build_application = base.build_application

    def build_application_with_content_admin():
        application = original_build_application()
        application.add_handler(
            CallbackQueryHandler(
                admin_unlock,
                pattern=r"^admin:unlock:(details|message|planet_venus|planet_mercury|planet_mars|planet_jupiter)(?::\d+)?$",
            )
        )
        return application

    base.build_application = build_application_with_content_admin
    _INSTALLED = True
    base.logger.info("CONTENT_ADMIN_ACCESS: contextual Premium unlock installed")
