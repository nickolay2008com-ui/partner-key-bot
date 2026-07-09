from __future__ import annotations

import asyncio
import logging
import platform
from typing import Any

from telegram import Update
from telegram.constants import ChatAction
from telegram.error import TelegramError
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
from app.ui.keyboards import (
    after_details_keyboard,
    cancel_keyboard,
    main_menu,
    report_keyboard,
)

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ASK_NAME, ASK_BIRTH_DATE = range(2)
LAST_REPORT_KEY = "last_partner_report"
MERCURY_BROADCAST_KEY = "mercury_retrograde_opportunity_2026_07"
MERCURY_BROADCAST_TEXT = """
🗣 Ретроградный Меркурий — окно возможностей

Сейчас хороший период не пугаться, а прояснять: детали, переписку, договорённости и то, что в отношениях осталось недосказанным.

Меркурий помогает понять, как человек мыслит, слышит, объясняет и договаривается.

В отношениях это шанс уточнить:
— что каждый имел в виду;
— где вас могли услышать не так;
— о чём пора поговорить спокойнее;
— какой маленький шаг вернёт ясность.

Откройте разбор и посмотрите блок:
🗣 Меркурий — как человек мыслит и договаривается

Иногда новый уровень начинается не с громкого решения, а с честного и ясного разговора.
""".strip()

WELCOME_TEXT = """
💞 Ключ к мужчине

Бот помогает женщине мягче понять мужчину по дате рождения: где ему эмоционально спокойно, как он проявляет чувства и как с ним говорить, чтобы обоим было хорошо.

Это не проверка совместимости и не приговор отношениям. Это карта понимания: как создать рядом состояние, куда человеку хочется возвращаться.

Команды:
/start — меню
/man — понять мужчину
/partner — быстрый ключ
/history — история разборов
/whoami — твой Telegram ID
""".strip()

ABOUT_TEXT = """
Что делает бот:

1. Берёт дату рождения мужчины.
2. Считает Луну, Венеру, Меркурий и Марс через Swiss Ephemeris.
3. Сначала даёт короткий бесплатный ключ: эмоциональный язык и первый шаг.
4. По кнопкам показывает глубину и помогает составить мягкое сообщение.

Без синастрии, процентов любви и космического суда. Только практичное понимание человека и отношений.
""".strip()

_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path, settings.database_url)
    return _store


def _user_id(update: Update) -> int | None:
    user = update.effective_user
    return user.id if user else None


def _is_authorized(update: Update) -> bool:
    if not settings.authorized_telegram_ids:
        return True
    user_id = _user_id(update)
    return bool(user_id and user_id in settings.authorized_telegram_ids)


def _is_broadcast_admin(update: Update) -> bool:
    user_id = _user_id(update)
    admin_ids = settings.broadcast_admin_ids | settings.authorized_telegram_ids
    return bool(user_id and user_id in admin_ids)


async def _remember_user(update: Update) -> None:
    user_id = _user_id(update)
    if user_id is not None:
        await asyncio.to_thread(get_store().register_user, user_id)


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
        await message.reply_text(
            chunk,
            disable_web_page_preview=True,
            **(kwargs if index == len(chunks) - 1 else {}),
        )


def _save_last_report(context: ContextTypes.DEFAULT_TYPE, report: PartnerReport) -> None:
    context.user_data[LAST_REPORT_KEY] = report.to_dict()


def _report_from_payload(payload: object) -> PartnerReport | None:
    if not isinstance(payload, dict):
        return None
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


def _load_last_report(context: ContextTypes.DEFAULT_TYPE) -> PartnerReport | None:
    return _report_from_payload(context.user_data.get(LAST_REPORT_KEY))


async def _load_last_report_for_user(update: Update, context: ContextTypes.DEFAULT_TYPE) -> PartnerReport | None:
    report = _load_last_report(context)
    if report is not None:
        return report
    user_id = _user_id(update)
    if user_id is None:
        return None
    payload = await asyncio.to_thread(get_store().latest_report_payload, user_id)
    report = _report_from_payload(payload)
    if report is not None:
        _save_last_report(context, report)
    return report


async def _send_mercury_broadcast(application: Application, *, force: bool = False) -> tuple[int, int, int, str]:
    store = get_store()
    if not force and await asyncio.to_thread(store.was_broadcast_sent, MERCURY_BROADCAST_KEY):
        return 0, 0, 0, "already_sent"

    user_ids = await asyncio.to_thread(store.all_user_ids)
    if not user_ids:
        return 0, 0, 0, "no_users"

    total = len(user_ids)
    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=MERCURY_BROADCAST_TEXT,
                disable_web_page_preview=True,
                reply_markup=main_menu(),
            )
        except TelegramError as exc:
            failed += 1
            logger.warning("MERCURY_BROADCAST: failed user_id=%s error=%s", user_id, exc)
        else:
            success += 1
        await asyncio.sleep(0.05)

    if success > 0:
        await asyncio.to_thread(store.mark_broadcast_sent, MERCURY_BROADCAST_KEY, total, success, failed)
    return total, success, failed, "sent"


async def _post_init(application: Application) -> None:
    try:
        total, success, failed, status = await _send_mercury_broadcast(application, force=False)
        logger.info(
            "MERCURY_BROADCAST_ON_BOOT: status=%s total=%s success=%s failed=%s",
            status,
            total,
            success,
            failed,
        )
    except Exception:
        logger.exception("MERCURY_BROADCAST_ON_BOOT_FAILED")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await update.effective_message.reply_text(WELCOME_TEXT, reply_markup=main_menu())


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _remember_user(update)
    user_id = _user_id(update)
    if user_id:
        await update.effective_message.reply_text(f"Твой Telegram ID: {user_id}")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await update.effective_message.reply_text(ABOUT_TEXT, reply_markup=main_menu())


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    user_id = _user_id(update)
    if user_id is None:
        return
    items = get_store().recent(user_id, limit=10)
    await update.effective_message.reply_text(format_history(items), reply_markup=main_menu())


async def broadcast_mercury(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_broadcast_admin(update):
        await update.effective_message.reply_text(
            "Команда рассылки доступна только админу. Добавь свой Telegram ID в BROADCAST_ADMIN_IDS или AUTHORIZED_TELEGRAM_IDS на Railway. Да, власть требует переменных окружения, как будто нам мало бюрократии в реальном мире."
        )
        return
    await _remember_user(update)
    wait = await update.effective_message.reply_text("Запускаю рассылку про ретроградный Меркурий…")
    total, success, failed, status = await _send_mercury_broadcast(context.application, force=True)
    await wait.edit_text(
        f"Рассылка завершена.\n\nСтатус: {status}\nВсего: {total}\nОтправлено: {success}\nОшибок: {failed}"
    )


async def partner_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END

    await _remember_user(update)
    context.user_data.pop("partner_name", None)
    await update.effective_message.reply_text(
        "Кого разбираем? Напиши имя мужчины или коротко: парень, муж, партнёр, Андрей.\n\nИмя нужно только для красивой карточки. Космосу всё равно, а интерфейсу приятно.",
        reply_markup=cancel_keyboard(),
    )
    return ASK_NAME


async def ask_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    await _remember_user(update)
    text = (update.effective_message.text or "").strip()
    if not text:
        await update.effective_message.reply_text("Напиши имя текстом. Например: Андрей")
        return ASK_NAME
    context.user_data["partner_name"] = text[:60]
    await update.effective_message.reply_text(
        "Теперь дата рождения мужчины.\n\nФормат: 12.04.1993\n\nВремя рождения пока не нужно. Если Луна в этот день меняла знак, бот честно покажет неоднозначность, без притворства астрологической всевидимости.",
        reply_markup=cancel_keyboard(),
    )
    return ASK_BIRTH_DATE


async def build_report_from_birth_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    await _remember_user(update)
    message = update.effective_message
    text = (message.text or "").strip()
    try:
        birth_date = parse_birth_date(text)
    except ValueError as exc:
        await message.reply_text(str(exc))
        return ASK_BIRTH_DATE

    partner_name = context.user_data.get("partner_name", "Партнёр")
    wait = await message.reply_text("Считаю эмоциональный язык…")
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
    except Exception:
        logger.exception("Failed to build partner report")
        safe_text = "Не получилось посчитать разбор. Проверь дату рождения в формате 12.04.1993 и попробуй ещё раз."
        try:
            await wait.edit_text(safe_text)
        except Exception:
            await message.reply_text(safe_text)

    return ConversationHandler.END


async def cancel_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    context.user_data.pop("partner_name", None)
    await update.effective_message.reply_text(
        "Ок, отменил. Отношения пока спасены от ещё одной формы ввода.",
        reply_markup=main_menu(),
    )
    return ConversationHandler.END


async def on_help_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await about(update, context)


async def on_history_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await history(update, context)


async def on_report_details_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    report = await _load_last_report_for_user(update, context)
    if report is None:
        await update.effective_message.reply_text(
            "Последний разбор не найден. Нажми /partner и сделай разбор заново.",
            reply_markup=main_menu(),
        )
        return
    await _send_long_text(update, report.text, reply_markup=after_details_keyboard())


async def on_report_message_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    report = await _load_last_report_for_user(update, context)
    if report is None:
        await update.effective_message.reply_text(
            "Последний разбор не найден. Нажми /partner и сделай разбор заново.",
            reply_markup=main_menu(),
        )
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

    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(_post_init).build()

    partner_flow = ConversationHandler(
        entry_points=[
            CommandHandler("partner", partner_start),
            CommandHandler("man", partner_start),
            CallbackQueryHandler(partner_start, pattern=r"^partner:start$"),
            CallbackQueryHandler(partner_start, pattern=r"^v2:man:start$"),
        ],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_birth_date)],
            ASK_BIRTH_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, build_report_from_birth_date)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_flow, pattern=r"^flow:cancel$"),
            CommandHandler("cancel", cancel_flow),
        ],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("history", history))
    app.add_handler(CommandHandler("broadcast_mercury", broadcast_mercury))
    app.add_handler(partner_flow)
    app.add_handler(CallbackQueryHandler(on_report_details_button, pattern=r"^report:details$"))
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
