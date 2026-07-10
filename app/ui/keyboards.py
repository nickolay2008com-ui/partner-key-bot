from __future__ import annotations

from urllib.parse import urlencode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config import settings


def detail_webapp_info(block: str) -> WebAppInfo:
    base_url = settings.webapp_url.rstrip("/")
    if base_url.endswith("/webapp"):
        base_url = base_url[: -len("/webapp")]
    return WebAppInfo(url=f"{base_url}/webapp/detail?{urlencode({'block': block})}")


V2_PRODUCT_BUTTONS = [
    [InlineKeyboardButton("1️⃣ Венера: как включить его нежность", web_app=detail_webapp_info("venus"))],
    [InlineKeyboardButton("2️⃣ Меркурий: слова, которые он слышит", web_app=detail_webapp_info("mercury"))],
    [InlineKeyboardButton("3️⃣ Марс: как дать ему силу действовать", web_app=detail_webapp_info("mars"))],
    [InlineKeyboardButton("4️⃣ Юпитер: куда вести вашу пару", web_app=detail_webapp_info("jupiter"))],
    [InlineKeyboardButton("🔓 Premium: мощная карта гармонии", web_app=detail_webapp_info("full"))],
    [InlineKeyboardButton("👤 Premium: глубокие портреты пары", web_app=detail_webapp_info("portrait"))],
]


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Понять мужчину", callback_data="v2:man:start")],
            [InlineKeyboardButton("🔑 Быстрый ключ", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
            [InlineKeyboardButton("ℹ️ Что это?", callback_data="help:about")],
        ]
    )


def report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔍 Показать глубже", web_app=detail_webapp_info("details"))],
            *V2_PRODUCT_BUTTONS,
            [InlineKeyboardButton("✍️ Premium: сообщение с эффектом", callback_data="report:message")],
            [InlineKeyboardButton("💞 Разобрать другого", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def profile_partner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Использовать сохранённые данные", callback_data="profile:use_partner")],
            [InlineKeyboardButton("✍️ Ввести новые данные", callback_data="profile:enter_partner")],
            [InlineKeyboardButton("Отмена", callback_data="flow:cancel")],
        ]
    )


def v2_report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            *V2_PRODUCT_BUTTONS,
            [InlineKeyboardButton("✍️ Что написать?", callback_data="report:message")],
            [InlineKeyboardButton("💞 Разобрать другого", callback_data="v2:man:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def v2_after_teaser_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            *V2_PRODUCT_BUTTONS,
            [InlineKeyboardButton("✍️ Что написать?", callback_data="report:message")],
            [InlineKeyboardButton("💞 Новый разбор", callback_data="v2:man:start")],
        ]
    )


def after_details_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            *V2_PRODUCT_BUTTONS,
            [InlineKeyboardButton("✍️ Premium: сообщение с эффектом", callback_data="report:message")],
            [InlineKeyboardButton("💞 Разобрать другого", callback_data="partner:start")],
            [InlineKeyboardButton("🗂 История", callback_data="history:show")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="flow:cancel")]])
