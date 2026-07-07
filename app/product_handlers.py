from __future__ import annotations

from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes

from app.astro.product_blocks import format_full_report_intro, format_mars_detail, format_mercury_detail, format_moon_detail, format_venus_detail
from app.astro.report import PartnerReport
from app.ui.product_keyboards import product_report_keyboard

LAST_REPORT_KEY = "last_partner_report"


def _load_last_report(context: ContextTypes.DEFAULT_TYPE) -> PartnerReport | None:
    payload = context.user_data.get(LAST_REPORT_KEY)
    if not isinstance(payload, dict):
        return None
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


async def _send(update: Update, context: ContextTypes.DEFAULT_TYPE, formatter) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    report = _load_last_report(context)
    if report is None:
        await update.effective_message.reply_text("Последний разбор не найден. Нажми /partner и сделай разбор заново.")
        return
    await update.effective_message.reply_text(formatter(report), disable_web_page_preview=True, reply_markup=product_report_keyboard())


async def moon_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, context, format_moon_detail)


async def venus_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, context, format_venus_detail)


async def mercury_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, context, format_mercury_detail)


async def mars_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, context, format_mars_detail)


async def full_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _send(update, context, format_full_report_intro)


def register_product_handlers(app) -> None:
    app.add_handler(CallbackQueryHandler(moon_detail, pattern=r"^v2:moon_detail$"))
    app.add_handler(CallbackQueryHandler(venus_detail, pattern=r"^v2:venus$"))
    app.add_handler(CallbackQueryHandler(mercury_detail, pattern=r"^v2:mercury$"))
    app.add_handler(CallbackQueryHandler(mars_detail, pattern=r"^v2:mars$"))
    app.add_handler(CallbackQueryHandler(full_report, pattern=r"^v2:full_report$"))
