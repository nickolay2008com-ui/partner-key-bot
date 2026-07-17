from __future__ import annotations

from typing import Any

from telegram.ext import CallbackQueryHandler

import app.entertaining_flow as entertaining_flow
import app.woman_flow as base

_INSTALLED = False


def _rub_price(product_key: str, fallback: int) -> str:
    product = base.get_product(product_key)
    rubles = product.rubles if product else fallback
    return f"{rubles} ₽"


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
    """All current relationship topics, shown directly without an intermediate menu."""
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton(
                    f"💗 Секреты любви — {_rub_price('planet_venus', 50)}",
                    callback_data="p:venus",
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"🗣 Стиль общения — {_rub_price('planet_mercury', 50)}",
                    callback_data="p:mercury",
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"🔥 Притяжение и инициатива — {_rub_price('planet_mars', 50)}",
                    callback_data="p:mars",
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"🪐 Рост пары — {_rub_price('planet_jupiter', 50)}",
                    callback_data="p:jupiter",
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"📖 Полная карта отношений — {_rub_price('details', 199)}",
                    callback_data="p:full",
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
            "Выберите один раздел:\n\n"
            "💗 Секреты любви — Венера пары\n"
            "🗣 Стиль общения — Меркурий пары\n"
            "🔥 Притяжение и инициатива — Марс пары\n"
            "🪐 Рост пары — Юпитер пары\n"
            "📖 Полная карта отношений — все темы вместе"
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
    base.logger.info("BRIDGE_NAVIGATION: two focused bridge actions and full topics menu installed")
