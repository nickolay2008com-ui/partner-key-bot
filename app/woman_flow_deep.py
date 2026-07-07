from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app import woman_flow as base
from app.astro.product_blocks import (
    format_full_report_intro,
    format_mars_detail,
    format_mercury_detail,
    format_moon_detail,
    format_venus_detail,
)

logger = logging.getLogger(__name__)


def _formatter(code: str):
    return {
        "moon": format_moon_detail,
        "venus": format_venus_detail,
        "mercury": format_mercury_detail,
        "mars": format_mars_detail,
        "full": format_full_report_intro,
    }.get(code)


async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    report = base._load_report(context, base.LAST_MAN_REPORT)
    if report is None:
        await update.effective_message.reply_text("Сначала сделай бесплатный разбор мужчины.", reply_markup=base.menu())
        return
    data = update.callback_query.data if update.callback_query else ""
    code = data.replace("p:", "")
    formatter = _formatter(code)
    if formatter is None:
        await update.effective_message.reply_text("Этот блок пока не найден.", reply_markup=base.after_bridge_keyboard())
        return
    await base._send_long(update, formatter(report), reply_markup=base.after_bridge_keyboard())


def build_application():
    base.product_preview = product_detail
    return base.build_application()


def main() -> None:
    logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
    logger.info("BOT_BOOT: starting deep woman flow")
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
