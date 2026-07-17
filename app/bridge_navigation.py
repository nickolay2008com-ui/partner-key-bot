from __future__ import annotations

from typing import Any

from telegram.ext import CallbackQueryHandler

import app.entertaining_flow as entertaining_flow
import app.woman_flow as base

_INSTALLED = False
_ORIGINAL_PREMIUM_OFFER = base.premium_offer
_ORIGINAL_PREMIUM_KEYBOARD = base.premium_keyboard
_ORIGINAL_YOOKASSA_PAYMENT_KEYBOARD = base.yookassa_payment_keyboard
_ORIGINAL_PAYMENT_RECOVERY_KEYBOARD = base.payment_recovery_keyboard
MAIN_MENU_BUTTON_TEXT = "🧭 Главное меню"


def _rub_price(product_key: str, fallback: int) -> str:
    product = base.get_product(product_key)
    rubles = product.rubles if product else fallback
    return f"{rubles} ₽"


def _replace_planets_back_button(
    markup: base.InlineKeyboardMarkup,
) -> base.InlineKeyboardMarkup:
    """Rename the legacy planets-back action without changing its callback route."""
    rows: list[list[base.InlineKeyboardButton]] = []
    for row in markup.inline_keyboard:
        updated_row: list[base.InlineKeyboardButton] = []
        for button in row:
            if str(button.callback_data or "").startswith("premium:planets") and button.text == "⬅️ К планетам":
                button = base.InlineKeyboardButton(
                    MAIN_MENU_BUTTON_TEXT,
                    callback_data=button.callback_data,
                )
            updated_row.append(button)
        rows.append(updated_row)
    return base.InlineKeyboardMarkup(rows)


def premium_keyboard_with_main_menu(product_key: str, report_id: int = 0) -> base.InlineKeyboardMarkup:
    return _replace_planets_back_button(_ORIGINAL_PREMIUM_KEYBOARD(product_key, report_id))


def yookassa_payment_keyboard_with_main_menu(
    product_key: str,
    payment_id: str,
    confirmation_url: str,
    report_id: int = 0,
) -> base.InlineKeyboardMarkup:
    return _replace_planets_back_button(
        _ORIGINAL_YOOKASSA_PAYMENT_KEYBOARD(
            product_key,
            payment_id,
            confirmation_url,
            report_id,
        )
    )


def payment_recovery_keyboard_with_main_menu(
    product_key: str,
    payment_id: str | None = None,
    report_id: int = 0,
) -> base.InlineKeyboardMarkup:
    return _replace_planets_back_button(_ORIGINAL_PAYMENT_RECOVERY_KEYBOARD(product_key, payment_id, report_id))


def bridge_actions_keyboard(report_id: int = 0) -> base.InlineKeyboardMarkup:
    """Two focused actions shown directly under the emotional bridge."""
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
                    "🧭 Посмотреть другие темы",
                    callback_data=base._callback_with_report("bridge:topics", report_id),
                )
            ],
        ]
    )


def other_topics_keyboard(report_id: int = 0) -> base.InlineKeyboardMarkup:
    """All current relationship topics, shown directly without an intermediate menu."""
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton(
                    f"💗 Секреты любви\nВенера — {_rub_price('planet_venus', 50)}",
                    callback_data=base._callback_with_report("p:venus", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"🗣 Стиль общения\nМеркурий — {_rub_price('planet_mercury', 50)}",
                    callback_data=base._callback_with_report("p:mercury", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"🔥 Притяжение и инициатива\nМарс — {_rub_price('planet_mars', 50)}",
                    callback_data=base._callback_with_report("p:mars", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"🪐 Рост пары\nЮпитер — {_rub_price('planet_jupiter', 50)}",
                    callback_data=base._callback_with_report("p:jupiter", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"📖 Полная карта отношений — {_rub_price('details', 199)}",
                    callback_data=base._callback_with_report("p:full", report_id),
                )
            ],
            [base.InlineKeyboardButton("🔄 Новый разбор", callback_data="start_man")],
        ]
    )


async def send_bridge_with_two_actions(update: Any, context: Any, text: str) -> None:
    """Send the bridge once; reveal the larger menu only when requested."""
    await base._send_long(
        update,
        context,
        text,
        reply_markup=bridge_actions_keyboard(base._current_report_id(context)),
    )


async def show_other_topics(update: Any, context: Any) -> None:
    query = update.callback_query
    raw_callback_data = str(getattr(query, "data", "") or "")
    callback_data, requested_report_id = base._callback_report(raw_callback_data)
    if query:
        await query.answer()

    if requested_report_id:
        if not await base._activate_report_context(update, context, requested_report_id):
            await base._tracked_reply_text(
                update,
                context,
                "Эта кнопка относится к недоступному разбору. Откройте нужную карту через историю.",
                reply_markup=base.menu(),
            )
            return
    if callback_data == "premium:planets":
        source_message = getattr(query, "message", None)
        if source_message is not None:
            try:
                await source_message.delete()
                base._forget_bot_message(context, source_message)
            except Exception:
                base.logger.exception("PLANET_CARD_DELETE_BEFORE_MAIN_MENU_FAILED")

    await base._remember_user(update)
    await base._track_event(
        update,
        "bridge_other_topics_opened",
        source="premium_planets" if callback_data == "premium:planets" else "bridge",
    )
    await base._tracked_reply_text(
        update,
        context,
        "🧭 Основное меню",
        reply_markup=other_topics_keyboard(base._current_report_id(context)),
    )


async def premium_offer_with_main_menu(update: Any, context: Any) -> None:
    """Route legacy “К планетам” buttons to the single current main menu."""
    query = update.callback_query
    callback_data, _ = base._callback_report(str(getattr(query, "data", "") or ""))
    if callback_data == "premium:planets":
        await show_other_topics(update, context)
        return
    await _ORIGINAL_PREMIUM_OFFER(update, context)


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Install after the payment layer so this wrapper preserves all existing handlers.
    original_build_application = base.build_application

    def build_application_with_bridge_topics():
        application = original_build_application()
        application.add_handler(CallbackQueryHandler(show_other_topics, pattern=r"^bridge:topics(?::\d+)?$"))
        return application

    base.bridge_summary_keyboard = bridge_actions_keyboard
    base._send_bridge_teaser_with_menu = send_bridge_with_two_actions
    entertaining_flow._send_bridge_teaser_with_menu = send_bridge_with_two_actions
    base.premium_offer = premium_offer_with_main_menu
    base.premium_keyboard = premium_keyboard_with_main_menu
    base.yookassa_payment_keyboard = yookassa_payment_keyboard_with_main_menu
    base.payment_recovery_keyboard = payment_recovery_keyboard_with_main_menu
    base.build_application = build_application_with_bridge_topics

    _INSTALLED = True
    base.logger.info("BRIDGE_NAVIGATION: two bridge actions and one main topics menu installed")
