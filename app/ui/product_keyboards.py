from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

PRODUCT_BUTTONS = [
    [InlineKeyboardButton("💗 Венера: как включить его нежность", callback_data="v2:venus")],
    [InlineKeyboardButton("🗣 Меркурий: слова, которые он слышит", callback_data="v2:mercury")],
    [InlineKeyboardButton("🔥 Марс: как дать ему силу", callback_data="v2:mars")],
    [InlineKeyboardButton("📖 Собрать весь разбор", callback_data="v2:full_report")],
]


def product_report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            *PRODUCT_BUTTONS,
            [InlineKeyboardButton("✍️ Что написать?", callback_data="report:message")],
            [InlineKeyboardButton("💞 Новый разбор", callback_data="v2:man:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )
