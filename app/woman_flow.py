from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import Application, ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, ConversationHandler, MessageHandler, filters

from app.astro.calculator import calculate_partner_chart, parse_birth_date
from app.astro.product_blocks import format_couple_full_report, format_couple_moon_bridge, format_mars_detail, format_mercury_detail, format_moon_detail, format_venus_detail
from app.astro.report import PartnerReport, build_partner_report, format_free_preview
from app.config import settings
from app.services.openai_client import build_partner_message_with_ai
from app.storage import ReportsStore, format_history

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)
ASK_MAN_NAME, ASK_MAN_DATE, ASK_WOMAN_NAME, ASK_WOMAN_DATE = range(4)
LAST_MAN_REPORT = "last_man_report"
LAST_WOMAN_REPORT = "last_woman_report"
_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path)
    return _store


def menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("💞 Начать разбор пары", callback_data="start_man")], [InlineKeyboardButton("🗂 История", callback_data="history")]])


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel")]])


def after_free_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("💞 Показать наш эмоциональный мост", callback_data="add_me")], [InlineKeyboardButton("💞 Новый разбор", callback_data="start_man")]])


def after_bridge_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌙 Луна мужчины: эмоциональный ритм", callback_data="p:moon")],
        [InlineKeyboardButton("💗 Венера: где появляется приятность", callback_data="p:venus")],
        [InlineKeyboardButton("🗣 Меркурий: как говорить мягче", callback_data="p:mercury")],
        [InlineKeyboardButton("🔥 Марс: как собирается сила", callback_data="p:mars")],
        [InlineKeyboardButton("📖 Карта гармонии пары", callback_data="p:full")],
        [InlineKeyboardButton("✍️ Что написать?", callback_data="message")],
        [InlineKeyboardButton("💞 Новый разбор", callback_data="start_man")],
    ])


def _user_id(update: Update) -> int | None:
    user = update.effective_user
    return user.id if user else None


def _is_authorized(update: Update) -> bool:
    if not settings.authorized_telegram_ids:
        return True
    user_id = _user_id(update)
    return bool(user_id and user_id in settings.authorized_telegram_ids)


async def _deny(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("Доступ закрыт. Добавь Telegram ID в AUTHORIZED_TELEGRAM_IDS.")


def _save_report(context: ContextTypes.DEFAULT_TYPE, key: str, report: PartnerReport) -> None:
    context.user_data[key] = report.to_dict()


def _load_report(context: ContextTypes.DEFAULT_TYPE, key: str) -> PartnerReport | None:
    payload = context.user_data.get(key)
    if not isinstance(payload, dict):
        return None
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


async def _send_long(update: Update, text: str, **kwargs: Any) -> None:
    message = update.effective_message
    if not message:
        return
    rest = text.strip()
    parts: list[str] = []
    while len(rest) > 3900:
        cut = rest.rfind("\n", 0, 3900)
        if cut < 1000:
            cut = 3900
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    for i, part in enumerate(parts):
        await message.reply_text(part, disable_web_page_preview=True, **(kwargs if i == len(parts) - 1 else {}))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    text = (
        "💞 Карта гармонии пары\n\n"
        "Поймите эмоциональный язык мужчины и ваш общий мост: где ему спокойнее, где хорошо вам, "
        "как говорить без давления и какой ритм помогает отношениям становиться теплее.\n\n"
        "Это не проверка совместимости и не приговор. Это карта понимания."
    )
    await update.effective_message.reply_text(text, reply_markup=menu())


async def start_man(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    context.user_data.pop("man_name", None)
    context.user_data.pop("woman_name", None)
    context.user_data.pop(LAST_MAN_REPORT, None)
    context.user_data.pop(LAST_WOMAN_REPORT, None)
    context.user_data.pop("last_partner_report", None)
    await update.effective_message.reply_text("Как зовут мужчину? Например: Андрей, муж, парень, партнёр.", reply_markup=cancel_keyboard())
    return ASK_MAN_NAME


async def ask_man_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.effective_message.text or "").strip()
    if not name:
        await update.effective_message.reply_text("Напиши имя текстом. Например: Андрей")
        return ASK_MAN_NAME
    context.user_data["man_name"] = name[:60]
    await update.effective_message.reply_text("Дата рождения мужчины. Формат: 12.04.1993", reply_markup=cancel_keyboard())
    return ASK_MAN_DATE


async def build_man_free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    message = update.effective_message
    try:
        birth_date = parse_birth_date((message.text or "").strip())
    except ValueError as exc:
        await message.reply_text(str(exc))
        return ASK_MAN_DATE
    wait = await message.reply_text("Считаю его эмоциональный язык…")
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        chart = await asyncio.to_thread(calculate_partner_chart, birth_date)
        report = await asyncio.to_thread(build_partner_report, chart, context.user_data.get("man_name", "мужчина"))
        _save_report(context, LAST_MAN_REPORT, report)
        context.user_data["last_partner_report"] = report.to_dict()
        user_id = _user_id(update)
        if user_id is not None:
            await asyncio.to_thread(get_store().add, user_id, report)
        try:
            await wait.delete()
        except Exception:
            pass
        text = (
            f"{format_free_preview(report)}\n\n"
            "💞 Хотите увидеть ваш общий эмоциональный мост?\n"
            "Добавьте вашу дату рождения — я покажу, где спокойнее ему, где хорошо вам, "
            "и какой ритм помогает быть ближе без давления."
        )
        await _send_long(update, text, reply_markup=after_free_keyboard())
    except Exception:
        logger.exception("Failed to build man report")
        await wait.edit_text("Не получилось посчитать. Проверь дату в формате 12.04.1993 и попробуй ещё раз.")
    return ConversationHandler.END


async def start_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if _load_report(context, LAST_MAN_REPORT) is None:
        await update.effective_message.reply_text("Сначала сделай бесплатный разбор мужчины.", reply_markup=menu())
        return ConversationHandler.END
    await update.effective_message.reply_text("Как вас назвать в разборе? Например: я, Анна, любимая.", reply_markup=cancel_keyboard())
    return ASK_WOMAN_NAME


async def ask_woman_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    name = (update.effective_message.text or "").strip()
    if not name:
        await update.effective_message.reply_text("Напиши имя текстом. Например: Анна")
        return ASK_WOMAN_NAME
    context.user_data["woman_name"] = name[:60]
    await update.effective_message.reply_text("Теперь ваша дата рождения. Формат: 12.04.1993", reply_markup=cancel_keyboard())
    return ASK_WOMAN_DATE


async def build_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    man_report = _load_report(context, LAST_MAN_REPORT)
    if man_report is None:
        await update.effective_message.reply_text("Сначала сделай разбор мужчины.", reply_markup=menu())
        return ConversationHandler.END
    message = update.effective_message
    try:
        birth_date = parse_birth_date((message.text or "").strip())
    except ValueError as exc:
        await message.reply_text(str(exc))
        return ASK_WOMAN_DATE
    wait = await message.reply_text("Сравниваю ваши эмоциональные языки…")
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        chart = await asyncio.to_thread(calculate_partner_chart, birth_date)
        woman_report = await asyncio.to_thread(build_partner_report, chart, context.user_data.get("woman_name", "вы"))
        _save_report(context, LAST_WOMAN_REPORT, woman_report)
        try:
            await wait.delete()
        except Exception:
            pass
        await _send_long(update, format_couple_moon_bridge(man_report, woman_report), reply_markup=after_bridge_keyboard())
    except Exception:
        logger.exception("Failed to build bridge")
        await wait.edit_text("Не получилось сравнить Луны. Проверь дату и попробуй ещё раз.")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    await update.effective_message.reply_text("Ок, остановил.", reply_markup=menu())
    return ConversationHandler.END


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    user_id = _user_id(update)
    if user_id is None:
        return
    await update.effective_message.reply_text(format_history(get_store().recent(user_id, limit=10)), reply_markup=menu())


async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    man_report = _load_report(context, LAST_MAN_REPORT)
    if man_report is None:
        await update.effective_message.reply_text("Сначала сделай бесплатный разбор мужчины.", reply_markup=menu())
        return
    woman_report = _load_report(context, LAST_WOMAN_REPORT)
    if woman_report is None:
        await update.effective_message.reply_text("Чтобы открыть глубокие блоки и карту гармонии пары, сначала добавьте вашу дату рождения.", reply_markup=after_free_keyboard())
        return
    code = (update.callback_query.data or "").replace("p:", "") if update.callback_query else ""
    if code == "full":
        await _send_long(update, format_couple_full_report(man_report, woman_report), reply_markup=after_bridge_keyboard())
        return
    formatters = {"moon": format_moon_detail, "venus": format_venus_detail, "mercury": format_mercury_detail, "mars": format_mars_detail}
    formatter = formatters.get(code)
    if formatter is None:
        await update.effective_message.reply_text("Этот блок пока не найден.", reply_markup=after_bridge_keyboard())
        return
    await _send_long(update, formatter(man_report), reply_markup=after_bridge_keyboard())


async def message_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    report = _load_report(context, LAST_MAN_REPORT)
    if report is None:
        await update.effective_message.reply_text("Сначала сделай разбор мужчины.", reply_markup=menu())
        return
    if _load_report(context, LAST_WOMAN_REPORT) is None:
        await update.effective_message.reply_text("Сначала добавьте вашу дату рождения и посмотрите эмоциональный мост. После этого я соберу варианты сообщения уже в контексте пары.", reply_markup=after_free_keyboard())
        return
    wait = await update.effective_message.reply_text("Собираю мягкие варианты сообщения…")
    text = await asyncio.to_thread(build_partner_message_with_ai, report)
    try:
        await wait.delete()
    except Exception:
        pass
    await update.effective_message.reply_text(text, reply_markup=after_bridge_keyboard())


def build_application() -> Application:
    settings.validate_runtime()
    app = ApplicationBuilder().token(settings.telegram_bot_token).build()
    man_flow = ConversationHandler(entry_points=[CommandHandler("man", start_man), CommandHandler("partner", start_man), CallbackQueryHandler(start_man, pattern=r"^start_man$")], states={ASK_MAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_man_date)], ASK_MAN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, build_man_free)]}, fallbacks=[CallbackQueryHandler(cancel, pattern=r"^cancel$"), CommandHandler("cancel", cancel)], allow_reentry=True)
    self_flow = ConversationHandler(entry_points=[CallbackQueryHandler(start_self, pattern=r"^add_me$")], states={ASK_WOMAN_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_woman_date)], ASK_WOMAN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, build_bridge)]}, fallbacks=[CallbackQueryHandler(cancel, pattern=r"^cancel$"), CommandHandler("cancel", cancel)], allow_reentry=True)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(man_flow)
    app.add_handler(self_flow)
    app.add_handler(CallbackQueryHandler(history, pattern=r"^history$"))
    app.add_handler(CallbackQueryHandler(product_detail, pattern=r"^p:(moon|venus|mercury|mars|full)$"))
    app.add_handler(CallbackQueryHandler(message_hint, pattern=r"^message$"))
    return app


def main() -> None:
    logger.info("BOT_BOOT: starting couple harmony flow")
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
