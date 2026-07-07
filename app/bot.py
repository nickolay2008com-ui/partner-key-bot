from __future__ import annotations

import asyncio
import logging
import platform
from typing import Any

from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from app.astro.calculator import calculate_partner_chart, parse_birth_date
from app.astro.report import PartnerReport, build_partner_report, format_free_preview
from app.config import settings
from app.services.openai_client import build_partner_message_with_ai
from app.storage import ReportsStore, format_history
from app.ui.keyboards import cancel_keyboard, main_menu, report_keyboard

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ASK_NAME, ASK_BIRTH_DATE = range(2)
LAST_REPORT_KEY = "last_partner_report"

WELCOME_TEXT = """
🔑 Ключ к партнёру

Бот помогает понять эмоциональный язык человека по дате рождения: что даёт ему доверие, как он проявляет чувства и как с ним лучше говорить.

Это не проверка совместимости и не приговор отношениям. Это мягкий переводчик различий, потому что люди почему-то до сих пор не поставляются с инструкцией.

Команды:
/start — меню
/partner — разобрать партнёра
/history — история разборов
/whoami — твой Telegram ID
""".strip()

ABOUT_TEXT = """
Что делает бот:

1. Берёт дату рождения партнёра.
2. Считает Луну, Венеру, Меркурий и Марс через Swiss Ephemeris.
3. Переводит это в простой язык:
— что человеку нужно для спокойствия;
— как он/она проявляет чувства;
— как говорить, чтобы вас услышали;
— чего лучше не делать;
— какой первый шаг выбрать.

Без синастрии, процентов любви и космического суда. Только практичное понимание человека.
""".strip()

_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path)
    return _store


def _user_id(update: Update) -> int | None:
    user = update.effective_user
    return user.id if user else None


def _is_authorized(update: Update) -> bool:
    if not settings.authorized_telegram_ids:
        return True
    user_id = _user_id(update)
    return bool(user_id and user_id in settings.authorized_telegram_ids)


async def _deny(update: Update) -> None:
    message = update.effective_message
    if message:
        await message.reply_text("Доступ закрыт. Добавь свой Telegram ID в AUTHORIZED_TELEGRAM_IDS на Railway.")


async def _send_long_text(update: Update, text: str, **kwargs: Any) -> None:
    message = update.effective_message
    if not message:
        return
    chunks: list[str] = []
    remaining = text.strip()
    while len(remaining) > 3900:
        split_at = remaining.rfind("\n", 0, 3900)
        if split_at < 1000:
            split_at = 3900
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)

    for index, chunk in enumerate(chunks):
        await message.reply_text(chunk, disable_web_page_preview=True, **(kwargs if index == len(chunks) - 1 else {}))


def _save_last_report(context: ContextTypes.DEFAULT_TYPE, report: PartnerReport) -> None:
    context.user_data[LAST_REPORT_KEY] = report.to_dict()


def _load_last_report(context: ContextTypes.DEFAULT_TYPE) -> PartnerReport | None:
    payload = context.user_data.get(LAST_REPORT_KEY)
    if not isinstance(payload, dict):
        return None
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await update.effective_message.reply_text(WELCOME_TEXT, reply_markup=main_menu())


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = _user_id(update)
    if user_id:
        await update.effective_message.reply_text(f"Твой Telegram ID: {user_id}")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await update.effective_message.reply_text(ABOUT_TEXT, reply_markup=main_menu())


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    user_id = _user_id(update)
    if user_id is None:
        return
    items = get_store().recent(user_id, limit=10)
    await update.effective_message.reply_text(format_history(items), reply_markup=main_menu())


async def partner_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END

    context.user_data.pop("partner_name", None)
    await update.effective_message.reply_text(
        "Кого разбираем? Напиши имя или коротко: партнёр, девушка, парень, Анна.\n\nЭто нужно только для красивой карточки, не для расчёта. Космосу всё равно, а интерфейсу приятно.",
        reply_markup=cancel_keyboard(),
    )
    return ASK_NAME


async def ask_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    text = (update.effective_message.text or "").strip()
    if not text:
        await update.effective_message.reply_text("Напиши имя текстом. Например: Анна")
        return ASK_NAME
    context.user_data["partner_name"] = text[:60]
    await update.effective_message.reply_text(
        "Теперь дата рождения.\n\nФормат: 12.04.1993\n\nВремя рождения пока не нужно. Если Луна в этот день меняла знак, бот честно покажет два варианта, без притворства астрологической всевидимости.",
        reply_markup=cancel_keyboard(),
    )
    return ASK_BIRTH_DATE


async def build_report_from_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    message = update.effective_message
    text = (message.text or "").strip()
    try:
        birth_date = parse_birth_date(text)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return ASK_BIRTH_DATE

    partner_name = context.user_data.get("partner_name", "Партнёр")
    wait = await message.reply_text("Считаю эмоциональный язык партнёра…")
    await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    try:
        chart = await asyncio.to_thread(calculate_partner_chart, birth_date)
        report = await asyncio.to_thread(build_partner_report, chart, partner_name)
        _save_last_report(context, report)
        user_id = _user_id(update)
        if user_id is not None:
            await asyncio.to_thread(get_store().add, user_id, report)
        try:
            await wait.delete()
        except Exception:
            pass
        await _send_long_text(update, format_free_preview(report), reply_markup=report_keyboard())
    except Exception as exc:
        logger.exception("Failed to build partner report")
        try:
            await wait.edit_text(f"Ошибка расчёта: {type(exc).__name__}: {exc}")
        except Exception:
            await message.reply_text(f"Ошибка расчёта: {type(exc).__name__}: {exc}")

    return ConversationHandler.END


async def cancel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    context.user_data.pop("partner_name", None)
    await update.effective_message.reply_text("Ок, отменил. Отношения пока спасены от ещё одной формы ввода.", reply_markup=main_menu())
    return ConversationHandler.END


async def on_help_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await about(update, context)


async def on_history_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await history(update, context)


async def on_report_message_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return
    report = _load_last_report(context)
    if report is None:
        await update.effective_message.reply_text("Последний разбор не найден. Нажми /partner и сделай разбор заново.", reply_markup=main_menu())
        return

    wait = await update.effective_message.reply_text("Собираю мягкие варианты сообщения…")
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
    text = await asyncio.to_thread(build_partner_message_with_ai, report)
    try:
        await wait.delete()
    except Exception:
        pass
    await update.effective_message.reply_text(text, disable_web_page_preview=True, reply_markup=report_keyboard())


def build_application() -> Application:
    settings.validate_runtime()
    logger.info("BOT_BOOT: Python %s on %s", platform.python_version(), platform.platform())
    logger.info("BOT_BOOT: %s", settings.diagnostic_summary())

    app = ApplicationBuilder().token(settings.telegram_bot_token).build()

    partner_flow = ConversationHandler(
        entry_points=[CommandHandler("partner", partner_start), CallbackQueryHandler(partner_start, pattern=r"^partner:start$")],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_birth_date)],
            ASK_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, build_report_from_birth_date)],
        },
        fallbacks=[CallbackQueryHandler(cancel_flow, pattern=r"^flow:cancel$"), CommandHandler("cancel", cancel_flow)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(partner_flow)
    app.add_handler(CallbackQueryHandler(on_report_message_button, pattern=r"^report:message$"))
    app.add_handler(CallbackQueryHandler(on_history_button, pattern=r"^history:show$"))
    app.add_handler(CallbackQueryHandler(on_help_button, pattern=r"^help:about$"))
    app.add_handler(CallbackQueryHandler(cancel_flow, pattern=r"^flow:cancel$"))
    return app


def main() -> None:
    try:
        app = build_application()
        logger.info("BOT_BOOT: starting long polling")
        app.run_polling(allowed_updates=Update.ALL_TYPES)
    except Exception:
        logger.exception("BOT_FAILED")
        raise


if __name__ == "__main__":
    main()
