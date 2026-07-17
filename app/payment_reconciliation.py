from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlencode

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

import app.button_contracts as contracts
import app.payment_checkout as checkout
import app.payments as payments
import app.webapp as webapp
import app.woman_flow as base

logger = logging.getLogger(__name__)

_INSTALLED = False
_RECONCILE_INTERVAL_SECONDS = 45
_DELIVERY_LEASE_SECONDS = 120
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
_ORIGINAL_PRECHECKOUT_CALLBACK = base.precheckout_callback
_ORIGINAL_SUCCESSFUL_PAYMENT = base.successful_payment


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


def _ensure_incidents_table(store: Any) -> None:
    query = """
        CREATE TABLE IF NOT EXISTS buyer_payment_incidents (
            reference_id TEXT PRIMARY KEY,
            provider TEXT NOT NULL,
            user_id BIGINT NOT NULL,
            reason TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(query)
        return
    with store._connect_sqlite() as conn:
        conn.execute(query.replace("BIGINT", "INTEGER"))


def _record_incident(
    store: Any,
    *,
    reference_id: str,
    provider: str,
    user_id: int,
    reason: str,
    payload: dict[str, Any],
) -> None:
    _ensure_incidents_table(store)
    now = _now()
    values = (
        reference_id,
        provider,
        user_id,
        reason[:300],
        json.dumps(payload, ensure_ascii=False, default=str)[:10000],
        "open",
        now,
        now,
    )
    query = """
        INSERT INTO buyer_payment_incidents (
            reference_id, provider, user_id, reason, payload_json, status, created_at, updated_at
        ) VALUES ({placeholders})
        ON CONFLICT(reference_id) DO UPDATE SET
            reason = excluded.reason,
            payload_json = excluded.payload_json,
            status = 'open',
            updated_at = excluded.updated_at
    """
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(query.format(placeholders="%s, %s, %s, %s, %s, %s, %s, %s"), values)
        return
    with store._connect_sqlite() as conn:
        conn.execute(query.format(placeholders="?, ?, ?, ?, ?, ?, ?, ?"), values)


def _list_open_incidents(store: Any, limit: int = 20) -> list[dict[str, Any]]:
    _ensure_incidents_table(store)
    safe_limit = max(1, min(int(limit), 100))
    if store.database_url:
        with store._connect_postgres() as conn:
            rows = conn.execute(
                """
                SELECT reference_id, provider, user_id, reason, created_at, updated_at
                FROM buyer_payment_incidents
                WHERE status = 'open'
                ORDER BY updated_at ASC
                LIMIT %s
                """,
                (safe_limit,),
            ).fetchall()
    else:
        with store._connect_sqlite() as conn:
            rows = conn.execute(
                """
                SELECT reference_id, provider, user_id, reason, created_at, updated_at
                FROM buyer_payment_incidents
                WHERE status = 'open'
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
    return [dict(row) for row in rows]


def _resolve_incident(store: Any, reference_id: str) -> None:
    _ensure_incidents_table(store)
    now = _now()
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                "UPDATE buyer_payment_incidents SET status = 'resolved', updated_at = %s WHERE reference_id = %s",
                (now, reference_id),
            )
        return
    with store._connect_sqlite() as conn:
        conn.execute(
            "UPDATE buyer_payment_incidents SET status = 'resolved', updated_at = ? WHERE reference_id = ?",
            (now, reference_id),
        )


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


def _claim_delivery(
    store: Any,
    *,
    payment_id: str,
    user_id: int,
    product_key: str,
    report_id: int,
) -> str:
    """Atomically claim one delivery across restarts and multiple bot processes."""
    _ensure_delivery_table(store)
    now = _now()
    stale_before = (datetime.now(timezone.utc) - timedelta(seconds=_DELIVERY_LEASE_SECONDS)).isoformat(
        timespec="seconds"
    )
    values = (payment_id, user_id, product_key, report_id, "processing", now)
    if store.database_url:
        with store._connect_postgres() as conn:
            inserted = conn.execute(
                """
                INSERT INTO yookassa_payment_deliveries (
                    payment_id, user_id, product_key, report_id, status,
                    attempts, last_error, updated_at, delivered_at
                )
                VALUES (%s, %s, %s, %s, %s, 1, '', %s, '')
                ON CONFLICT(payment_id) DO NOTHING
                RETURNING payment_id
                """,
                values,
            ).fetchone()
            if inserted:
                return "claimed"
            row = conn.execute(
                "SELECT status FROM yookassa_payment_deliveries WHERE payment_id = %s",
                (payment_id,),
            ).fetchone()
            current_status = str(row["status"] or "") if row else ""
            if current_status == "delivered":
                return "already_delivered"
            if current_status == "manual_review":
                return "manual_review"
            claimed = conn.execute(
                """
                UPDATE yookassa_payment_deliveries
                SET status = 'processing', attempts = attempts + 1, last_error = '', updated_at = %s
                WHERE payment_id = %s
                  AND status <> 'delivered'
                  AND (status <> 'processing' OR updated_at < %s)
                RETURNING payment_id
                """,
                (now, payment_id, stale_before),
            ).fetchone()
            return "claimed" if claimed else "processing"

    with store._connect_sqlite() as conn:
        inserted = conn.execute(
            """
            INSERT INTO yookassa_payment_deliveries (
                payment_id, user_id, product_key, report_id, status,
                attempts, last_error, updated_at, delivered_at
            )
            VALUES (?, ?, ?, ?, ?, 1, '', ?, '')
            ON CONFLICT(payment_id) DO NOTHING
            """,
            values,
        )
        if inserted.rowcount == 1:
            return "claimed"
        row = conn.execute(
            "SELECT status FROM yookassa_payment_deliveries WHERE payment_id = ?",
            (payment_id,),
        ).fetchone()
        current_status = str(row["status"] or "") if row else ""
        if current_status == "delivered":
            return "already_delivered"
        if current_status == "manual_review":
            return "manual_review"
        claimed = conn.execute(
            """
            UPDATE yookassa_payment_deliveries
            SET status = 'processing', attempts = attempts + 1, last_error = '', updated_at = ?
            WHERE payment_id = ?
              AND status <> 'delivered'
              AND (status <> 'processing' OR updated_at < ?)
            """,
            (now, payment_id, stale_before),
        )
        return "claimed" if claimed.rowcount == 1 else "processing"


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
                    attempts = yookassa_payment_deliveries.attempts,
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
                attempts = yookassa_payment_deliveries.attempts,
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

    metadata_payload = str(metadata.get("payload") or "").strip()
    if metadata_payload:
        parsed_payload = payments.parse_payload(metadata_payload)
        if parsed_payload != (product_key, report_id):
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


async def _notify_admins(application: Application, text: str) -> None:
    admin_ids = base.settings.broadcast_admin_ids | base.settings.authorized_telegram_ids
    for admin_id in admin_ids:
        try:
            await application.bot.send_message(chat_id=admin_id, text=text, disable_web_page_preview=True)
        except TelegramError:
            logger.warning("BUYER_PROTECTION_ADMIN_NOTIFY_FAILED: admin_id=%s", admin_id)


def _short_reference(payment_id: str) -> str:
    compact = payment_id.replace("stars:", "").strip()
    return compact[-12:] if compact else "не определён"


def _open_keyboard(product_key: str, report_id: int = 0) -> InlineKeyboardMarkup | None:
    if product_key in _PLANET_BLOCKS:
        block, label = _PLANET_BLOCKS[product_key]
        return InlineKeyboardMarkup([[InlineKeyboardButton(label, web_app=base.detail_webapp_info(block, report_id))]])
    if product_key == "details":
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "📖 Открыть полную карту отношений",
                        web_app=base.detail_webapp_info("full", report_id),
                    )
                ]
            ]
        )
    return None


async def _deliver_purchase(
    application: Application,
    *,
    payment: dict[str, Any],
    user_id: int,
    product_key: str,
    report_id: int,
    recovery: bool = False,
) -> None:
    store = base.get_store()
    payload = store.report_payload(user_id, report_id)
    report = webapp._report_from_payload(payload)
    if report is None:
        raise ValueError("Не найден разбор, к которому относится платёж.")

    contracts.set_active_report(store, user_id, report_id)
    receipt_note = _receipt_note(payment)
    success_title = "🛟 Покупка восстановлена." if recovery else "✅ Оплата подтверждена."

    if product_key in _PLANET_BLOCKS:
        block, _ = _PLANET_BLOCKS[product_key]
        woman_report = contracts._woman_report(store, user_id)
        text = contracts._format_pair_topic(report, woman_report, block)
        await _send_text_parts(
            application,
            user_id=user_id,
            text=f"{success_title} Ваш купленный разбор готов.{receipt_note}\n\n{text}",
            reply_markup=_open_keyboard(product_key, report_id),
        )
        return

    if product_key == "message":
        text = base.format_message_guidance(report)
        await _send_text_parts(
            application,
            user_id=user_id,
            text=f"{success_title} Вот купленный материал.{receipt_note}\n\n{text}",
        )
        return

    if product_key == "details":
        await application.bot.send_message(
            chat_id=user_id,
            text=(
                f"{success_title} Полная карта отношений открыта для этого разбора."
                f"{receipt_note}\n\nНажмите кнопку ниже: она откроет именно оплаченную карту."
            ),
            reply_markup=_open_keyboard(product_key, report_id),
        )
        return

    raise ValueError(f"Неизвестный платный продукт: {product_key}")


async def _process_payment(application: Application, payment: dict[str, Any]) -> str:
    purchase = _validated_purchase(payment)
    if purchase is None:
        return "ignored"

    payment_id, user_id, product_key, report_id = purchase
    store = base.get_store()
    claim = _claim_delivery(
        store,
        payment_id=payment_id,
        user_id=user_id,
        product_key=product_key,
        report_id=report_id,
    )
    if claim == "already_delivered":
        await asyncio.to_thread(checkout.delete_checkout_session, store, user_id, product_key, report_id)
        return "already_delivered"
    if claim == "manual_review":
        return "manual_review"
    if claim != "claimed":
        return "processing"

    if store.report_payload(user_id, report_id) is None:
        _record_delivery(
            store,
            payment_id=payment_id,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            status="manual_review",
            error="report_not_found",
        )
        _record_incident(
            store,
            reference_id=f"yookassa:{payment_id}",
            provider="yookassa",
            user_id=user_id,
            reason="paid_report_not_found",
            payload={"payment_id": payment_id, "product_key": product_key, "report_id": report_id},
        )
        reference = _short_reference(payment_id)
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=(
                    "⚠️ Оплата подтверждена, но бот не смог автоматически восстановить связанную карту. "
                    "Покупка зафиксирована и передана на ручное восстановление — повторно платить не нужно.\n\n"
                    f"Номер обращения: {reference}"
                ),
            )
        except TelegramError:
            logger.warning("BUYER_PROTECTION_NOTICE_FAILED: payment_id=%s", payment_id)
        await _notify_admins(
            application,
            "🚨 Оплаченный товар требует ручного восстановления\n\n"
            f"Платёж: {payment_id}\nПользователь: {user_id}\n"
            f"Продукт: {product_key}\nОтчёт: {report_id}\nПричина: report_not_found",
        )
        return "manual_review"

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
    await asyncio.to_thread(checkout.delete_checkout_session, store, user_id, product_key, report_id)
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
        "processing": 0,
        "manual_review": 0,
        "pending": 0,
        "canceled": 0,
        "api_error": 0,
        "ignored": 0,
    }
    if not base.settings.yookassa_enabled:
        return summary

    async with _reconcile_lock():
        try:
            recent = await asyncio.to_thread(
                _list_recent_payments,
                shop_id=base.settings.yookassa_shop_id or "",
                secret_key=base.settings.yookassa_secret_key or "",
                limit=100,
            )
        except Exception:
            logger.exception("YOOKASSA_RECENT_LIST_FAILED: falling back to durable checkout sessions")
            recent = []
            summary["api_error"] += 1

        payments_by_id = {str(item.get("id") or ""): item for item in recent if str(item.get("id") or "").strip()}
        sessions = await asyncio.to_thread(checkout.list_checkout_sessions, base.get_store(), 1000)
        sessions_by_id = {str(item["payment_id"]): item for item in sessions if item.get("payment_id")}
        for payment_id in sessions_by_id:
            if payment_id in payments_by_id:
                continue
            try:
                payments_by_id[payment_id] = await asyncio.to_thread(
                    _get_payment_raw,
                    shop_id=base.settings.yookassa_shop_id or "",
                    secret_key=base.settings.yookassa_secret_key or "",
                    payment_id=payment_id,
                )
            except Exception:
                logger.exception("YOOKASSA_SESSION_CHECK_FAILED: payment_id=%s", payment_id)
                summary["api_error"] += 1

        summary["scanned"] = len(payments_by_id)
        for payment in reversed(list(payments_by_id.values())):
            payment_id = str(payment.get("id") or "")
            status = str(payment.get("status") or "")
            session = sessions_by_id.get(payment_id)
            if session and status == "canceled":
                await asyncio.to_thread(
                    checkout.delete_checkout_session,
                    base.get_store(),
                    int(session["user_id"]),
                    str(session["product_key"]),
                    int(session["report_id"]),
                )
                summary["canceled"] += 1
                continue
            if session and status in {"pending", "waiting_for_capture"}:
                summary["pending"] += 1
                continue
            try:
                result = await _process_payment(application, payment)
            except Exception:
                logger.exception("YOOKASSA_PAYMENT_PROCESS_FAILED: payment_id=%s", payment_id)
                result = "failed"
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
            if (
                summary["delivered"]
                or summary["retry"]
                or summary["failed"]
                or summary["manual_review"]
                or summary["api_error"]
            ):
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

    if payment_id:
        try:
            result = await _reconcile_payment_id(context.application, payment_id)
            if result == "delivered":
                if query:
                    await query.answer()
                context.user_data.pop(base.PENDING_YOOKASSA_PAYMENT, None)
                return
            if result == "manual_review":
                if query:
                    await query.answer()
                await base._tracked_reply_text(
                    update,
                    context,
                    "Оплата подтверждена и зафиксирована, но товар требует ручного восстановления. "
                    "Повторно платить не нужно — администратор уже получил уведомление.",
                    reply_markup=base.menu(),
                )
                return
        except Exception:
            logger.exception("YOOKASSA_CHECK_DELIVERY_FAILED: payment_id=%s", payment_id)

    await _ORIGINAL_YOOKASSA_PAYMENT_CHECK(update, context)


def _purchase_label(product_key: str) -> str:
    product = payments.get_product(product_key)
    return product.title if product else product_key


def _purchases_keyboard(store: Any, user_id: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for item in store.list_entitlements(user_id, limit=30):
        product_key = str(item["product_key"])
        report_id = int(item["report_id"])
        if payments.get_product(product_key) is None or report_id <= 0:
            continue
        payload = store.report_payload(user_id, report_id)
        partner_name = (
            str(payload.get("partner_name") or "карта") if isinstance(payload, dict) else f"карта #{report_id}"
        )
        label = f"{_purchase_label(product_key)} · {partner_name}"[:60]
        rows.append(
            [
                InlineKeyboardButton(
                    f"🛟 {label}",
                    callback_data=f"purchase:open:{product_key}:{report_id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)


async def _purchases_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = base._user_id(update)
    message = update.effective_message
    if user_id is None or message is None:
        return
    store = base.get_store()
    purchases = await asyncio.to_thread(store.list_entitlements, user_id, 30)
    if not purchases:
        await message.reply_text(
            "У вас пока нет сохранённых покупок. После оплаты товар появится здесь и останется доступен после перезапуска бота.",
            reply_markup=base.menu(),
        )
        return
    await message.reply_text(
        "🛟 Мои покупки\n\n"
        "Здесь можно повторно получить любой оплаченный материал. Повторная выдача бесплатна и не создаёт новый платёж.",
        reply_markup=_purchases_keyboard(store, user_id),
    )


async def _purchase_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = base._user_id(update)
    if query:
        await query.answer()
    if query is None or user_id is None:
        return
    parts = str(query.data or "").split(":", 3)
    if len(parts) != 4:
        await query.message.reply_text("Не удалось распознать покупку. Откройте «Мои покупки» ещё раз.")
        return
    product_key = parts[2]
    try:
        report_id = int(parts[3])
    except (TypeError, ValueError):
        report_id = 0
    store = base.get_store()
    if (
        payments.get_product(product_key) is None
        or report_id <= 0
        or not await asyncio.to_thread(store.has_entitlement, user_id, product_key, report_id)
    ):
        await query.message.reply_text("Эта покупка не принадлежит вашему Telegram-профилю.")
        return
    if store.report_payload(user_id, report_id) is None:
        reference = f"entitlement:{user_id}:{product_key}:{report_id}"
        await asyncio.to_thread(
            _record_incident,
            store,
            reference_id=reference,
            provider="entitlement",
            user_id=user_id,
            reason="recovery_report_not_found",
            payload={"product_key": product_key, "report_id": report_id},
        )
        await query.message.reply_text(
            "Покупка найдена, но связанная карта требует ручного восстановления. "
            "Повторно платить не нужно — обращение уже зафиксировано."
        )
        await _notify_admins(
            context.application,
            "🚨 Покупатель запросил восстановление товара\n\n"
            f"Пользователь: {user_id}\nПродукт: {product_key}\nОтчёт: {report_id}",
        )
        return
    try:
        await _deliver_purchase(
            context.application,
            payment={},
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            recovery=True,
        )
    except Exception as exc:
        logger.exception("PURCHASE_SELF_SERVICE_RECOVERY_FAILED: user_id=%s", user_id)
        await query.message.reply_text(
            "Покупка сохранена, но повторная отправка сейчас не удалась. Попробуйте ещё раз через минуту — платить повторно не нужно."
        )
        store.track_event(
            user_id,
            "purchase_recovery_failed",
            {"product_key": product_key, "report_id": report_id, "error": str(exc)[:300]},
        )
        return
    store.track_event(user_id, "purchase_self_service_recovered", {"product_key": product_key, "report_id": report_id})


async def _protected_precheckout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return
    parsed = payments.parse_payload(query.invoice_payload)
    user_id = base._user_id(update)
    if parsed is None or user_id is None:
        await query.answer(ok=False, error_message="Не получилось распознать покупку. Откройте оплату заново.")
        return
    product_key, report_id = parsed
    product = payments.get_product(product_key)
    store = base.get_store()
    if product is None or report_id <= 0 or store.report_payload(user_id, report_id) is None:
        await query.answer(ok=False, error_message="Карта для этой покупки не найдена. Откройте её заново в боте.")
        return
    if query.currency != payments.CURRENCY_STARS or query.total_amount != product.stars:
        await query.answer(ok=False, error_message="Сумма покупки изменилась. Закройте оплату и откройте её заново.")
        return
    if await base._has_premium_access(update, context, product_key, report_id):
        await query.answer(ok=False, error_message="Этот материал уже куплен. Откройте раздел «Мои покупки».")
        return
    await query.answer(ok=True)
    await base._track_event(update, "premium_precheckout_approved", product_key=product_key, report_id=report_id)


async def _protected_successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    successful = update.effective_message.successful_payment if update.effective_message else None
    user_id = base._user_id(update)
    if successful is None or user_id is None:
        await _ORIGINAL_SUCCESSFUL_PAYMENT(update, context)
        return
    charge_id = str(successful.telegram_payment_charge_id or successful.provider_payment_charge_id or "").strip()
    delivery_id = f"stars:{charge_id or f'{user_id}:{int(datetime.now(timezone.utc).timestamp())}'}"
    parsed = payments.parse_payload(successful.invoice_payload)
    store = base.get_store()
    if parsed is None:
        await asyncio.to_thread(
            _record_incident,
            store,
            reference_id=delivery_id,
            provider="telegram_stars",
            user_id=user_id,
            reason="unrecognized_invoice_payload",
            payload={"invoice_payload": successful.invoice_payload, "charge_id": charge_id},
        )
        await _send_text_parts(
            context.application,
            user_id=user_id,
            text=(
                "⚠️ Оплата получена, но бот не распознал товар. Повторно платить не нужно: покупка зафиксирована "
                f"для ручной выдачи. Номер обращения: {_short_reference(delivery_id)}"
            ),
        )
        await _notify_admins(
            context.application,
            f"🚨 Не распознан платёж Stars\nПользователь: {user_id}\nПлатёж: {delivery_id}",
        )
        return

    product_key, report_id = parsed
    product = payments.get_product(product_key)
    if product is None or report_id <= 0 or store.report_payload(user_id, report_id) is None:
        await asyncio.to_thread(
            _record_incident,
            store,
            reference_id=delivery_id,
            provider="telegram_stars",
            user_id=user_id,
            reason="paid_product_or_report_not_found",
            payload={"product_key": product_key, "report_id": report_id, "charge_id": charge_id},
        )
        await _send_text_parts(
            context.application,
            user_id=user_id,
            text=(
                "⚠️ Оплата подтверждена, но товар требует ручного восстановления. Повторно платить не нужно. "
                f"Номер обращения: {_short_reference(delivery_id)}"
            ),
        )
        await _notify_admins(
            context.application,
            "🚨 Оплаченный Stars-товар требует восстановления\n"
            f"Пользователь: {user_id}\nПлатёж: {delivery_id}\nПродукт: {product_key}\nОтчёт: {report_id}",
        )
        return

    if successful.currency != payments.CURRENCY_STARS or successful.total_amount != product.stars:
        await asyncio.to_thread(
            _record_incident,
            store,
            reference_id=delivery_id,
            provider="telegram_stars",
            user_id=user_id,
            reason="paid_amount_mismatch_product_delivered",
            payload={
                "product_key": product_key,
                "report_id": report_id,
                "currency": successful.currency,
                "total_amount": successful.total_amount,
                "expected": product.stars,
            },
        )
        await _notify_admins(
            context.application,
            "⚠️ Несовпадение суммы Stars; товар выдан в пользу покупателя\n"
            f"Пользователь: {user_id}\nПлатёж: {delivery_id}\nПродукт: {product_key}",
        )

    await asyncio.to_thread(store.grant_entitlement, user_id, product_key, report_id, delivery_id)
    claim = await asyncio.to_thread(
        _claim_delivery,
        store,
        payment_id=delivery_id,
        user_id=user_id,
        product_key=product_key,
        report_id=report_id,
    )
    if claim == "already_delivered":
        await _send_text_parts(
            context.application,
            user_id=user_id,
            text="Покупка уже была выдана. Её всегда можно открыть через раздел «🛟 Мои покупки».",
            reply_markup=_purchases_keyboard(store, user_id),
        )
        return
    if claim != "claimed":
        return
    try:
        await _deliver_purchase(
            context.application,
            payment={},
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
        )
    except TelegramError as exc:
        _record_delivery(
            store,
            payment_id=delivery_id,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            status="retry",
            error=str(exc),
        )
        logger.warning("STARS_DELIVERY_RETRY: payment_id=%s", delivery_id)
        return
    except Exception as exc:
        _record_delivery(
            store,
            payment_id=delivery_id,
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            status="failed",
            error=str(exc),
        )
        logger.exception("STARS_DELIVERY_FAILED: payment_id=%s", delivery_id)
        return
    _record_delivery(
        store,
        payment_id=delivery_id,
        user_id=user_id,
        product_key=product_key,
        report_id=report_id,
        status="delivered",
    )
    store.track_event(
        user_id,
        "premium_payment_auto_delivered",
        {"provider": "telegram_stars", "product_key": product_key, "report_id": report_id},
    )


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
        f"Ручное восстановление: {summary['manual_review']}\n"
        f"Ошибки выдачи: {summary['failed']}\n"
        f"Ошибки API: {summary['api_error']}"
    )


async def _payment_incidents_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not base._is_broadcast_admin(update):
        await base._deny(update)
        return
    message = update.effective_message
    if message is None:
        return
    incidents = await asyncio.to_thread(_list_open_incidents, base.get_store(), 20)
    if not incidents:
        await message.reply_text("Открытых платёжных инцидентов нет.")
        return
    lines = ["🚨 Покупки, требующие ручной проверки", ""]
    for item in incidents:
        lines.extend(
            [
                f"{item['reference_id']}",
                f"Провайдер: {item['provider']} · пользователь: {item['user_id']}",
                f"Причина: {item['reason']} · создано: {item['created_at']}",
                "",
            ]
        )
    lines.append("После проверки: /restore_purchase USER_ID PRODUCT_KEY REPORT_ID REFERENCE")
    await message.reply_text("\n".join(lines))


async def _restore_purchase_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not base._is_broadcast_admin(update):
        await base._deny(update)
        return
    message = update.effective_message
    if message is None:
        return
    if len(context.args) != 4:
        await message.reply_text("Формат: /restore_purchase USER_ID PRODUCT_KEY REPORT_ID REFERENCE")
        return
    try:
        user_id = int(context.args[0])
        product_key = str(context.args[1])
        report_id = int(context.args[2])
        reference = str(context.args[3])
    except (TypeError, ValueError):
        await message.reply_text("USER_ID и REPORT_ID должны быть числами.")
        return
    store = base.get_store()
    if user_id <= 0 or report_id <= 0 or payments.get_product(product_key) is None:
        await message.reply_text("Неизвестный пользователь, продукт или отчёт.")
        return
    if store.report_payload(user_id, report_id) is None:
        await message.reply_text("Отчёт не принадлежит этому пользователю. Сначала восстановите исходную карту.")
        return
    await asyncio.to_thread(store.grant_entitlement, user_id, product_key, report_id, f"manual:{reference}")
    try:
        await _deliver_purchase(
            context.application,
            payment={},
            user_id=user_id,
            product_key=product_key,
            report_id=report_id,
            recovery=True,
        )
    except Exception:
        logger.exception("MANUAL_PURCHASE_RESTORE_FAILED: reference=%s", reference)
        await message.reply_text(
            "Доступ сохранён, но Telegram не доставил сообщение. Покупатель увидит товар в «Мои покупки»."
        )
        return
    await asyncio.to_thread(_resolve_incident, store, reference)
    store.track_event(
        user_id,
        "purchase_manually_restored",
        {"product_key": product_key, "report_id": report_id, "reference": reference},
    )
    await message.reply_text("Покупка восстановлена и повторно доставлена покупателю.")


def _build_application_with_payment_reconciliation() -> Application:
    application = _ORIGINAL_BUILD_APPLICATION()
    application.add_handler(CommandHandler("reconcile_payments", _reconcile_command))
    application.add_handler(CommandHandler("payment_incidents", _payment_incidents_command))
    application.add_handler(CommandHandler("restore_purchase", _restore_purchase_command))
    application.add_handler(CommandHandler("purchases", _purchases_command))
    application.add_handler(CallbackQueryHandler(_purchases_command, pattern=r"^purchases$"))
    application.add_handler(
        CallbackQueryHandler(
            _purchase_open,
            pattern=r"^purchase:open:(details|message|planet_venus|planet_mercury|planet_mars|planet_jupiter):\d+$",
        )
    )
    return application


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    base._post_init = _post_init_with_payment_reconciliation
    base.yookassa_payment_check = _payment_check_with_delivery
    base.precheckout_callback = _protected_precheckout
    base.successful_payment = _protected_successful_payment
    base.build_application = _build_application_with_payment_reconciliation

    _INSTALLED = True
    logger.info("YOOKASSA_RECONCILIATION: automatic payment delivery installed")
