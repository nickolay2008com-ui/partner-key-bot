from __future__ import annotations

from typing import Any

from telegram.ext import CallbackQueryHandler

import app.entertaining_flow as entertaining_flow
import app.woman_flow as base

_INSTALLED = False


def bridge_actions_keyboard() -> base.InlineKeyboardMarkup:
    """Two focused actions shown directly under the emotional bridge."""
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
                    "🧭 Посмотреть другие темы",
                    callback_data="bridge:topics",
                )
            ],
        ]
    )


def other_topics_keyboard() -> base.InlineKeyboardMarkup:
    details_product = base.get_product("details")
    message_product = base.get_product("message")
    details_price = f" — {details_product.rubles} ₽" if details_product else ""
    message_price = f" — {message_product.rubles} ₽" if message_product else ""

    return base.InlineKeyboardMarkup(
        [
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
            [
                base.InlineKeyboardButton(
                    f"✍️ 2 варианта сообщения{message_price}",
                    callback_data="message",
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
        reply_markup=bridge_actions_keyboard(),
    )


async def show_other_topics(update: Any, context: Any) -> None:
    query = update.callback_query
    if query:
        await query.answer()

    await base._remember_user(update)
    await base._track_event(update, "bridge_other_topics_opened")
    await base._tracked_reply_text(
        update,
        context,
        (
            "🧭 Другие темы\n\n"
            "Выберите, что хочется понять дальше: язык симпатии, стиль разговора, "
            "инициативу, направление роста пары или конкретный следующий шаг."
        ),
        reply_markup=other_topics_keyboard(),
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    # Install after the payment layer so this wrapper preserves all existing handlers.
    original_build_application = base.build_application

    def build_application_with_bridge_topics():
        application = original_build_application()
        application.add_handler(
            CallbackQueryHandler(show_other_topics, pattern=r"^bridge:topics$")
        )
        return application

    base.bridge_summary_keyboard = bridge_actions_keyboard
    base._send_bridge_teaser_with_menu = send_bridge_with_two_actions
    entertaining_flow._send_bridge_teaser_with_menu = send_bridge_with_two_actions
    base.build_application = build_application_with_bridge_topics

    _INSTALLED = True
    base.logger.info("BRIDGE_NAVIGATION: two focused bridge actions installed")
