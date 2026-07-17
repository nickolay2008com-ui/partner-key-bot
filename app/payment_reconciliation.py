from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CommandHandler, ContextTypes

import app.button_contracts as contracts
import app.payments as payments
import app.webapp as webapp
import app.woman_flow as base

logger = logging.getLogger(__name__)

_INSTALLED = False
_RECONCILE_INTERVAL_SECONDS = 45
_RECONCILE_LOCK: asyncio.Lock | None = None

_PLANET_BLOCKS = {
    "planet_venus": ("venus", "💗 Открыть оплаченный разбор Венеры"),
    "planet_mercury": ("mercury", "🗣 Открыть оплаченный разбор Меркурия"),
    "planet_mars": ("mars", "🔥 Открыть оплаченный разбор Марса"),
    "planet_jupiter": ("jupiter", "🪐 Открыть оплаченный разбор Юпитера"),
}

_ORIGINAL_POST_INIT = base._post_init
_ORIGINAL_BUILD_APPLICATION = base.build_application
_ORIGINAL_YOOKASSA_PAYMENT_CHECK = base.yookassa_payment_check


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _ensure_delivery_table(store: Any) -> None:
    query = """
        CREATE TABLE IF NOT EXISTS yookassa_payment_deliveries (
            payment_id TEXT PRIMARY KEY,
            user_id BIGINT NOT NULL,
            product_key TEXT NOT NULL,
            report_id BIGINT NOT NULL,
            status TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            delivered_at TEXT NOT NULL DEFAULT ''
        )
    """
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(query)
        return
    with store._connect_sqlite() as conn:
        conn.execute(query.replace("BIGINT", "INTEGER"))


def _delivery_status(store: Any, payment_id: str) -> str:
    _ensure_delivery_table(store)
    if store.database_url:
        with store._connect_postgres() as conn:
            row = conn.execute(
                "SELECT status FROM yookassa_payment_deliveries WHERE payment_id = %s",
                (payment_id,),
            ).fetchone()
    else:
        with store._connect_sqlite() as conn:
            row = conn.execute(
                "SELECT status FROM yookassa_payment_deliveries WHERE payment_id = ?",
                (payment_id,),
            ).fetchone()
    return str(row["status"] or "") if row else ""


def _record_delivery(
    store: Any,
    *,
    payment_id: str,
    user_id: int,
    product_key: str,
    report_id: int,
    status: str,
    error: str = "",
) -> None:
    _ensure_delivery_table(store)
    now = _now()
    delivered_at = now if status == "delivered" else ""
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                """
                INSERT INTO yookassa_payment_deliveries (
                    payment_id, user_id, product_key, report_id, status,
                    attempts, last_error, updated_at, delivered_at
                )
                VALUES (%s, %s, %s, %s, %s, 1, %s, %s, %s)
                ON CONFLICT(payment_id) DO UPDATE SET
                    user_id = excluded.user_id,
                    product_key = excluded.product_key,
                    report_id = excluded.report_id,
                    status = excluded.status,
                    attempts = yookassa_payment_deliveries.attempts + 1,
                    last_error = excluded.last_error,
                    updated_at = excluded.updated_at,
                    delivered_at = CASE
                        WHEN excluded.delivered_at <> '' THEN excluded.delivered_at
                        ELSE yookassa_payment_deliveries.delivered_at
                    END
                """,
                (
                    payment_id,
                    user_id,
                    product_key,
                    report_id,
                    status,
                    error[:1000],
                    now,
                    delivered_at,
                ),
            )
        return

    with store._connect_sqlite() as conn:
        conn.execute(
            """
            INSERT INTO yookassa_payment_deliveries (
                payment_id, user_id, product_key, report_id, status,
                attempts, last_error, updated_at, delivered_at
            )
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
            ON CONFLICT(payment_id) DO UPDATE SET
                user_id = excluded.user_id,
                product_key = excluded.product_key,
                report_id = excluded.report_id,
                status = excluded.status,
                attempts = yookassa_payment_deliveries.attempts + 1,
                last_error = excluded.last_error,
                updated_at = excluded.updated_at,
                delivered_at = CASE
                    WHEN excluded.delivered_at <> '' THEN excluded.delivered_at
                    ELSE yookassa_payment_deliveries.delivered_at
                END
            """,
            (
                payment_id,
                user_id,
                product_key,
                report_id,
                status,
                error[:1000],
                now,
                delivered_at,
            ),
        )


def _list_recent_payments(*, shop_id: str, secret_key: str, limit: int = 100) -> list[dict[str, Any]]:
    query = urlencode({"limit": max(1, min(limit, 100))})
    payload = payments._yookassa_request(
        shop_id,
        secret_key,
        "GET",
        f"{payments.YOOKASSA_API_URL}?{query}",
    )
    items = payload.get("items") if isinstance(payload, dict) else None
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _get_payment_raw(*, shop_id: str, secret_key: str, payment_id: str) -> dict[str, Any]:
    payload = payments._yookassa_request(
        shop_id,
        secret_key,
        "GET",
        f"{payments.YOOKASSA_API_URL}/{payment_id}",
    )
    return payload if isinstance(payload, dict) else {}


def _validated_purchase(payment: dict[str, Any]) -> tuple[str, int, str, int] | None:
    payment_id = str(payment.get("id") or "").strip()
    if not payment_id or payment.get("status") != "succeeded" or payment.get("paid") is not True:
        return None

    metadata = payment.get("metadata")
    if not isinstance(metadata, dict):
        return None

    product_key = str(metadata.get("product_key") or "").strip()
    product = payments.get_product(product_key)
    if product is None:
        return None

    try:
        user_id = int(metadata.get("telegram_user_id") or 0)
        report_id = int(metadata.get("report_id") or 0)
    except (TypeError, ValueError):
        return None
    if user_id <= 0 or report_id <= 0:
        return None

    amount = payment.get("amount")
    if not isinstance(amount, dict) or str(amount.get("currency") or "") != payments.CURRENCY_RUB:
        return None
    try:
        actual_amount = Decimal(str(amount.get("value") or ""))
    except (InvalidOperation, ValueError):
        return None
    if actual_amount != Decimal(product.rub_amount):
        return None

    return payment_id, user_id, product_key, report_id


def _receipt_note(payment: dict[str, Any]) -> str:
    if payment.get("test") is True:
        return "\n\n🧾 Это тестовый платёж: настоящий фискальный чек на email в тестовом режиме не отправляется."

    status = str(payment.get("receipt_registration") or "").strip().lower()
    if status == "succeeded":
        return "\n\n🧾 ЮKassa сообщает, что чек зарегистрирован. Письмо отправляет кассовая система на указанный email."
    if status == "pending":
        return "\n\n🧾 Чек ещё регистрируется. Его письмо может прийти немного позже."
    if status == "canceled":
        return "\n\n⚠️ Платёж успешен, но регистрация чека отменена. Нужно проверить фискализацию магазина ЮKassa."
    return ""


def _split_text(text: str, limit: int = 3900) -> list[str]:
    rest = text.strip()
    parts: list[str] = []
    while len(rest) > limit:
        cut = rest.rfind("\n", 0, limit)
        if cut < 1000:
            cut = limit
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    return parts


async def _send_text_parts(
    application: Application,
    *,
    user_id: int,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    parts = _split_text(text)
    for index, part in enumerate(parts):
        await application.bot.send_message(
            chat_id=user_id,
            text=part,
            reply_markup=reply_markup if index == len(parts) - 1 else None,
            disable_web_page_preview=True,
        )


def _open_keyboard(product_key: str) -> InlineKeyboardMarkup | None:
    if product_key in _PLANET_BLOCKS:
        block, label = _PLANET_BLOCKS[product_key]
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton(label, web_app=base.detail_webapp_info(block))]]
        )
    if product_key == "details":
        return InlineKeyboardMarkup(
            [[InlineKeyboardButton("📖 Открыть полную карту отношений", web_app=base.detail_webapp_info("full"))]]
        )
    return None


async def _deliver_purchase(
    application: Application,
    *,
    payment: dict[str, Any],
    user_id: int,
    product_key: str,
    report_id: int,
) -> None:
    store = base.get_store()
    payload = store.report_payload(user_id, report_id)
    report = webapp._report_from_payload(payload)
    if report is None:
        raise ValueError("Не найден разбор, к которому относится платёж.")

    contracts.set_active_report(store, user_id, report_id)
    receipt_note = _receipt_note(payment)

    if product_key in _PLANET_BLOCKS:
        block, _ = _PLANET_BLOCKS[product_key]
        woman_report = contracts._woman_report(store, user_id)
        text = contracts._format_pair_topic(report, woman_report, block)
        await _send_text_parts(
            application,
            user_id=user_id,
            text=f"✅ Оплата подтверждена. Ваш купленный разбор готов.{receipt_note}\n\n{text}",
            reply_markup=_open_keyboard(product_key),
        )
        return

    if product_key == "message":
        text = base.format_message_guidance(report)
        await _send_text_parts(
            application,
            user_id=user_id,
            text=f"✅ Оплата подтверждена. Вот ваши варианты сообщения.{receipt_note}\n\n{text}",
        )
        return

    if product_key == "details":
        await application.bot.send_message(
            chat_id=user_id,
            text=(
                "✅ Оплата подтверждена. Полная карта отношений открыта для этого разбора."
                f"{receipt_note}\n\nНажмите кнопку ниже: она откроет именно оплаченную карту."
            ),
            reply_markup=_open_keyboard(product_key),
        )
        return

    raise ValueError(f"Неизвестный платный продукт: {product_key}")


async def _process_payment(application: Application, payment: dict[str, Any]) -> str:
    purchase = _validated_purchase(payment)
    if purchase is None:
        return "ignored"

    payment_id, user_id, product_key, report_id = purchase
    store = base.get_store()
    if _delivery_status(store, payment_id) == "delivered":
        return "already_delivered"

    if store.report_payload(user_id, report_id) is None:
        _record_delivery(
            store,
            payment_id=payment_id,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            status="failed",
            error="report_not_found",
        )
        return "report_not_found"

    store.grant_entitlement(user_id, product_key, report_id, payment_id)
    try:
        await _deliver_purchase(
            application,
            payment=payment,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
        )
    except TelegramError as exc:
        _record_delivery(
            store,
            payment_id=payment_id,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            status="retry",
            error=str(exc),
        )
        logger.warning("YOOKASSA_DELIVERY_RETRY: payment_id=%s error=%s", payment_id, exc)
        return "retry"
    except Exception as exc:
        _record_delivery(
            store,
            payment_id=payment_id,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            status="failed",
            error=str(exc),
        )
        logger.exception("YOOKASSA_DELIVERY_FAILED: payment_id=%s", payment_id)
        return "failed"

    _record_delivery(
        store,
        payment_id=payment_id,
        user_id=user_id,
        product_key=product_key,
        report_id=report_id,
        status="delivered",
    )
    store.track_event(
        user_id,
        "premium_payment_auto_delivered",
        {
            "payment_id": payment_id,
            "product_key": product_key,
            "report_id": report_id,
        },
    )
    return "delivered"


def _reconcile_lock() -> asyncio.Lock:
    global _RECONCILE_LOCK
    if _RECONCILE_LOCK is None:
        _RECONCILE_LOCK = asyncio.Lock()
    return _RECONCILE_LOCK


async def reconcile_recent_payments(application: Application) -> dict[str, int]:
    summary = {
        "scanned": 0,
        "delivered": 0,
        "already_delivered": 0,
        "retry": 0,
        "failed": 0,
        "ignored": 0,
    }
    if not base.settings.yookassa_enabled:
        return summary

    async with _reconcile_lock():
        recent = await asyncio.to_thread(
            _list_recent_payments,
            shop_id=base.settings.yookassa_shop_id or "",
            secret_key=base.settings.yookassa_secret_key or "",
            limit=100,
        )
        summary["scanned"] = len(recent)
        for payment in reversed(recent):
            result = await _process_payment(application, payment)
            summary[result] = summary.get(result, 0) + 1
    return summary


async def _reconcile_payment_id(application: Application, payment_id: str) -> str:
    if not base.settings.yookassa_enabled or not payment_id:
        return "ignored"
    payment = await asyncio.to_thread(
        _get_payment_raw,
        shop_id=base.settings.yookassa_shop_id or "",
        secret_key=base.settings.yookassa_secret_key or "",
        payment_id=payment_id,
    )
    async with _reconcile_lock():
        return await _process_payment(application, payment)


async def _reconciliation_loop(application: Application) -> None:
    while True:
        try:
            summary = await reconcile_recent_payments(application)
            if summary["delivered"] or summary["retry"] or summary["failed"]:
                logger.info("YOOKASSA_RECONCILE: %s", summary)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("YOOKASSA_RECONCILE_FAILED")
        await asyncio.sleep(_RECONCILE_INTERVAL_SECONDS)


async def _post_init_with_payment_reconciliation(application: Application) -> None:
    await _ORIGINAL_POST_INIT(application)
    if base.settings.yookassa_enabled:
        application.create_task(
            _reconciliation_loop(application),
            name="yookassa-payment-reconciliation",
        )


async def _payment_check_with_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    payment_id = ""
    if query and query.data and query.data.startswith("premium:check:"):
        payment_id = query.data.replace("premium:check:", "", 1).strip()

    await _ORIGINAL_YOOKASSA_PAYMENT_CHECK(update, context)

    if payment_id:
        try:
            await _reconcile_payment_id(context.application, payment_id)
        except Exception:
            logger.exception("YOOKASSA_CHECK_DELIVERY_FAILED: payment_id=%s", payment_id)


async def _reconcile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not base._is_broadcast_admin(update):
        await base._deny(update)
        return

    message = update.effective_message
    if message is None:
        return

    await message.reply_text("Проверяю последние платежи ЮKassa и восстанавливаю невыданные покупки…")
    try:
        summary = await reconcile_recent_payments(context.application)
    except Exception:
        logger.exception("YOOKASSA_RECONCILE_COMMAND_FAILED")
        await message.reply_text("Не получилось связаться с ЮKassa. Проверьте ключи и логи Railway.")
        return

    await message.reply_text(
        "Сверка завершена.\n\n"
        f"Проверено: {summary['scanned']}\n"
        f"Выдано сейчас: {summary['delivered']}\n"
        f"Уже было выдано: {summary['already_delivered']}\n"
        f"Ожидают повторной отправки: {summary['retry']}\n"
        f"Ошибки: {summary['failed']}"
    )


def _build_application_with_payment_reconciliation() -> Application:
    application = _ORIGINAL_BUILD_APPLICATION()
    application.add_handler(CommandHandler("reconcile_payments", _reconcile_command))
    return application


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    base._post_init = _post_init_with_payment_reconciliation
    base.yookassa_payment_check = _payment_check_with_delivery
    base.build_application = _build_application_with_payment_reconciliation

    _INSTALLED = True
    logger.info("YOOKASSA_RECONCILIATION: automatic payment delivery installed")
