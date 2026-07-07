from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Понять мужчину", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
            [InlineKeyboardButton("ℹ️ Что это?", callback_data="help:about")],
        ]
    )


def report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🌙 Точная Луна мужчины", callback_data="report:moon")],
            [InlineKeyboardButton("💞 Добавить мою дату", callback_data="self:start")],
            [InlineKeyboardButton("💗 Венера: где ему приятно", callback_data="report:venus")],
            [InlineKeyboardButton("🗣 Меркурий: как с ним говорить", callback_data="report:mercury")],
            [InlineKeyboardButton("🔥 Марс: как поддержать", callback_data="report:mars")],
            [InlineKeyboardButton("📖 Весь разбор", callback_data="report:details")],
            [InlineKeyboardButton("✍️ Что написать?", callback_data="report:message")],
            [InlineKeyboardButton("💞 Разобрать другого", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def after_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Добавить мою дату", callback_data="self:start")],
            [InlineKeyboardButton("✍️ Что написать?", callback_data="report:message")],
            [InlineKeyboardButton("💞 Разобрать другого", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="flow:cancel")]])
