from __future__ import annotations

import app.woman_flow as base

_INSTALLED = False


def compact_planets_keyboard() -> base.InlineKeyboardMarkup:
    """Compact paid-topic menu with user-facing benefit names."""
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton("💗 Секреты любви — 50 ₽", callback_data="p:venus"),
                base.InlineKeyboardButton("🗣 Разговор — 50 ₽", callback_data="p:mercury"),
            ],
            [
                base.InlineKeyboardButton("🔥 Инициатива — 50 ₽", callback_data="p:mars"),
                base.InlineKeyboardButton("🪐 Рост — 50 ₽", callback_data="p:jupiter"),
            ],
            [base.InlineKeyboardButton("📖 Всё меню", callback_data="premium:back")],
        ]
    )


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    base.compact_planets_keyboard = compact_planets_keyboard
    _INSTALLED = True
    base.logger.info("TOPIC_LABELS: Venus renamed to Secrets of Love")
