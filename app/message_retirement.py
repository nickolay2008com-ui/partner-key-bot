from __future__ import annotations

from typing import Any, Awaitable, Callable

import app.bridge_navigation as bridge_navigation
import app.button_contracts as button_contracts
import app.entertaining_flow as entertaining_flow
import app.woman_flow as base

_INSTALLED = False


def active_topics_keyboard() -> base.InlineKeyboardMarkup:
    """Current paid navigation without the retired message-writing product."""
    details_product = base.get_product("details")
    details_price = f" — {details_product.rubles} ₽" if details_product else ""
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton(
                    "💞 Открыть полный эмоциональный мост",
                    web_app=base.detail_webapp_info("bridge"),
                )
            ],
            [
                base.InlineKeyboardButton(
                    "💗🗣🔥🪐 Выбрать отдельную тему — 50 ₽",
                    callback_data="premium:planets",
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"📖 Полная карта отношений{details_price}",
                    callback_data="p:full",
                )
            ],
            [base.InlineKeyboardButton("🔄 Новый разбор", callback_data="start_man")],
        ]
    )


def other_topics_keyboard() -> base.InlineKeyboardMarkup:
    """Use the single authoritative menu owned by bridge navigation."""
    return bridge_navigation.other_topics_keyboard()


async def retired_message_route(update: Any, context: Any) -> None:
    """Gracefully handle buttons that were already sent before the feature was removed."""
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    await base._remember_user(update)
    await base._track_event(update, "retired_message_product_opened")
    text = (
        "🧭 Этот раздел больше не используется.\n\n"
        "Ниже доступны все актуальные темы пары и полная карта отношений."
    )
    if query and query.message:
        try:
            await base._tracked_replace_callback_text(
                update,
                context,
                text,
                reply_markup=other_topics_keyboard(),
            )
            return
        except Exception:
            base.logger.exception("RETIRED_MESSAGE_BUTTON_REPLACE_FAILED")
    await base._tracked_reply_text(
        update,
        context,
        text,
        reply_markup=other_topics_keyboard(),
    )


def _retire_product_handler(
    original: Callable[[Any, Any], Awaitable[None]],
    *,
    callback_prefixes: tuple[str, ...],
) -> Callable[[Any, Any], Awaitable[None]]:
    async def wrapped(update: Any, context: Any) -> None:
        data = update.callback_query.data if update.callback_query else ""
        if any(data == prefix or data.startswith(prefix) for prefix in callback_prefixes):
            await retired_message_route(update, context)
            return
        await original(update, context)

    return wrapped


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    original_premium_offer = base.premium_offer
    original_premium_buy = base.premium_buy

    base.read_menu_keyboard = active_topics_keyboard
    button_contracts.relationship_menu_keyboard = active_topics_keyboard
    entertaining_flow._relationship_menu_keyboard = active_topics_keyboard

    base.message_hint = retired_message_route
    base.premium_offer = _retire_product_handler(
        original_premium_offer,
        callback_prefixes=("premium:message",),
    )
    base.premium_buy = _retire_product_handler(
        original_premium_buy,
        callback_prefixes=("premium:buy:message",),
    )

    _INSTALLED = True
    base.logger.info("MESSAGE_RETIREMENT: message product removed; full topics menu preserved")
