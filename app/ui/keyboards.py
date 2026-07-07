from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔑 Понять партнёра", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
            [InlineKeyboardButton("ℹ️ Что это?", callback_data="help:about")],
        ]
    )


def report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔍 Открыть глубокий ключ", callback_data="unlock:details")],
            [InlineKeyboardButton("✍️ Открыть тексты сообщения", callback_data="unlock:message")],
            [InlineKeyboardButton("🔑 Разобрать другого", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def paid_result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔑 Разобрать другого", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="flow:cancel")]])
