from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

import app.payments as payments

PENDING_RECEIPT_PRODUCT = "pending_receipt_product"
PENDING_RECEIPT_REPORT_ID = "pending_receipt_report_id"
_CHECKOUT_LOCKS: dict[tuple[int, str, int], asyncio.Lock] = {}

_EMAIL_RE = re.compile(
    r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+$"
)


def normalize_receipt_email(value: str) -> str:
    email = (value or "").strip().lower()
    if len(email) > 254 or not _EMAIL_RE.fullmatch(email):
        raise ValueError("Похоже, в email есть ошибка. Отправьте адрес целиком, например name@yandex.ru")
    return email


def _ensure_payment_contacts_table(store: Any) -> None:
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS payment_contacts (
                    user_id BIGINT PRIMARY KEY,
                    receipt_email TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
        return
    with store._connect_sqlite() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS payment_contacts (
                user_id INTEGER PRIMARY KEY,
                receipt_email TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def get_receipt_email(store: Any, user_id: int) -> str:
    _ensure_payment_contacts_table(store)
    if store.database_url:
        with store._connect_postgres() as conn:
            row = conn.execute(
                "SELECT receipt_email FROM payment_contacts WHERE user_id = %s",
                (user_id,),
            ).fetchone()
    else:
        with store._connect_sqlite() as conn:
            row = conn.execute(
                "SELECT receipt_email FROM payment_contacts WHERE user_id = ?",
                (user_id,),
            ).fetchone()
    if not row:
        return ""
    try:
        return normalize_receipt_email(str(row["receipt_email"] or ""))
    except ValueError:
        return ""


def save_receipt_email(store: Any, user_id: int, email: str) -> str:
    clean_email = normalize_receipt_email(email)
    _ensure_payment_contacts_table(store)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                """
                INSERT INTO payment_contacts (user_id, receipt_email, updated_at)
                VALUES (%s, %s, %s)
                ON CONFLICT(user_id) DO UPDATE SET
                    receipt_email = excluded.receipt_email,
                    updated_at = excluded.updated_at
                """,
                (user_id, clean_email, now),
            )
    else:
        with store._connect_sqlite() as conn:
            conn.execute(
                """
                INSERT INTO payment_contacts (user_id, receipt_email, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    receipt_email = excluded.receipt_email,
                    updated_at = excluded.updated_at
                """,
                (user_id, clean_email, now),
            )
    return clean_email


def _ensure_checkout_sessions_table(store: Any) -> None:
    query = """
        CREATE TABLE IF NOT EXISTS yookassa_checkout_sessions (
            user_id BIGINT NOT NULL,
            product_key TEXT NOT NULL,
            report_id BIGINT NOT NULL,
            payment_id TEXT NOT NULL,
            confirmation_url TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY (user_id, product_key, report_id)
        )
    """
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(query)
        return
    with store._connect_sqlite() as conn:
        conn.execute(query.replace("BIGINT", "INTEGER"))


def get_checkout_session(store: Any, user_id: int, product_key: str, report_id: int) -> dict[str, str] | None:
    _ensure_checkout_sessions_table(store)
    if store.database_url:
        with store._connect_postgres() as conn:
            row = conn.execute(
                """
                SELECT payment_id, confirmation_url
                FROM yookassa_checkout_sessions
                WHERE user_id = %s AND product_key = %s AND report_id = %s
                """,
                (user_id, product_key, report_id),
            ).fetchone()
    else:
        with store._connect_sqlite() as conn:
            row = conn.execute(
                """
                SELECT payment_id, confirmation_url
                FROM yookassa_checkout_sessions
                WHERE user_id = ? AND product_key = ? AND report_id = ?
                """,
                (user_id, product_key, report_id),
            ).fetchone()
    if not row:
        return None
    return {
        "payment_id": str(row["payment_id"] or ""),
        "confirmation_url": str(row["confirmation_url"] or ""),
    }


def list_checkout_sessions(store: Any, limit: int = 500) -> list[dict[str, Any]]:
    """Return durable payment ids so reconciliation does not depend on YooKassa's recent-payment window."""
    _ensure_checkout_sessions_table(store)
    safe_limit = max(1, min(int(limit), 1000))
    if store.database_url:
        with store._connect_postgres() as conn:
            rows = conn.execute(
                """
                SELECT user_id, product_key, report_id, payment_id, confirmation_url, updated_at
                FROM yookassa_checkout_sessions
                ORDER BY updated_at ASC
                LIMIT %s
                """,
                (safe_limit,),
            ).fetchall()
    else:
        with store._connect_sqlite() as conn:
            rows = conn.execute(
                """
                SELECT user_id, product_key, report_id, payment_id, confirmation_url, updated_at
                FROM yookassa_checkout_sessions
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (safe_limit,),
            ).fetchall()
    return [
        {
            "user_id": int(row["user_id"]),
            "product_key": str(row["product_key"] or ""),
            "report_id": int(row["report_id"]),
            "payment_id": str(row["payment_id"] or ""),
            "confirmation_url": str(row["confirmation_url"] or ""),
            "updated_at": str(row["updated_at"] or ""),
        }
        for row in rows
    ]


def save_checkout_session(
    store: Any,
    user_id: int,
    product_key: str,
    report_id: int,
    payment_id: str,
    confirmation_url: str,
) -> None:
    _ensure_checkout_sessions_table(store)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    values = (user_id, product_key, report_id, payment_id, confirmation_url, now)
    query = """
        INSERT INTO yookassa_checkout_sessions (
            user_id, product_key, report_id, payment_id, confirmation_url, updated_at
        ) VALUES ({placeholders})
        ON CONFLICT(user_id, product_key, report_id) DO UPDATE SET
            payment_id = excluded.payment_id,
            confirmation_url = excluded.confirmation_url,
            updated_at = excluded.updated_at
    """
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(query.format(placeholders="%s, %s, %s, %s, %s, %s"), values)
        return
    with store._connect_sqlite() as conn:
        conn.execute(query.format(placeholders="?, ?, ?, ?, ?, ?"), values)


def delete_checkout_session(store: Any, user_id: int, product_key: str, report_id: int) -> None:
    _ensure_checkout_sessions_table(store)
    if store.database_url:
        with store._connect_postgres() as conn:
            conn.execute(
                """
                DELETE FROM yookassa_checkout_sessions
                WHERE user_id = %s AND product_key = %s AND report_id = %s
                """,
                (user_id, product_key, report_id),
            )
        return
    with store._connect_sqlite() as conn:
        conn.execute(
            """
            DELETE FROM yookassa_checkout_sessions
            WHERE user_id = ? AND product_key = ? AND report_id = ?
            """,
            (user_id, product_key, report_id),
        )


def _checkout_lock(user_id: int, product_key: str, report_id: int) -> asyncio.Lock:
    key = (user_id, product_key, report_id)
    lock = _CHECKOUT_LOCKS.get(key)
    if lock is None:
        lock = asyncio.Lock()
        _CHECKOUT_LOCKS[key] = lock
    return lock


def _masked_email(email: str) -> str:
    local, _, domain = email.partition("@")
    if len(local) <= 2:
        masked_local = local[:1] + "*"
    else:
        masked_local = local[:2] + "*" * min(5, len(local) - 2)
    return f"{masked_local}@{domain}"


def create_yookassa_payment_with_receipt(
    *,
    shop_id: str,
    secret_key: str,
    product: payments.Product,
    product_key: str,
    report_id: int,
    user_id: int,
    return_url: str,
    receipt_email: str,
) -> payments.YooKassaPayment:
    email = normalize_receipt_email(receipt_email)
    payload = {
        "amount": {"value": product.rub_amount, "currency": payments.CURRENCY_RUB},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": f"{product.title} для отчёта #{report_id}",
        "receipt": {
            "customer": {"email": email},
            "items": [
                {
                    "description": product.title[:128],
                    "quantity": "1.00",
                    "amount": {"value": product.rub_amount, "currency": payments.CURRENCY_RUB},
                    "vat_code": 1,
                    "payment_mode": "full_payment",
                    "payment_subject": "service",
                }
            ],
        },
        "metadata": {
            "product_key": product_key,
            "report_id": str(report_id),
            "telegram_user_id": str(user_id),
            "payload": payments.make_payload(product_key, report_id),
        },
    }
    raw = payments._yookassa_request(shop_id, secret_key, "POST", payments.YOOKASSA_API_URL, payload)
    confirmation = raw.get("confirmation") if isinstance(raw.get("confirmation"), dict) else {}
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    confirmation_url = confirmation.get("confirmation_url")
    if not payments._is_valid_confirmation_url(confirmation_url):
        raise payments.YooKassaPaymentError(
            "ЮKassa создала платёж, но не вернула рабочую ссылку. Попробуйте открыть оплату ещё раз.",
            f"Missing or invalid YooKassa confirmation_url for payment {raw.get('id', '')}",
        )
    return payments.YooKassaPayment(
        payment_id=str(raw.get("id", "")),
        status=str(raw.get("status", "")),
        confirmation_url=str(confirmation_url).strip(),
        paid=bool(raw.get("paid")),
        metadata={str(key): str(value) for key, value in metadata.items()},
    )


def _email_prompt_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("← Вернуться к разбору", callback_data="premium:back")]])


def _receipt_configuration_keyboard(base: Any, product_key: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("← Вернуться к разбору", callback_data="premium:back")]]
    if product_key in base.PLANET_PAYWALL_COPY:
        rows.insert(0, [InlineKeyboardButton("⬅️ К планетам", callback_data="premium:planets")])
    return InlineKeyboardMarkup(rows)


async def _open_yookassa_checkout(
    base: Any,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    product_key: str,
    report_id: int,
    user_id: int,
    receipt_email: str,
) -> None:
    product = payments.get_product(product_key)
    if product is None:
        await base._tracked_reply_text(
            update, context, "Не получилось определить покупку. Откройте её из меню ещё раз."
        )
        return

    await base._track_event(
        update,
        "premium_yookassa_payment_started",
        product_key=product_key,
        report_id=report_id,
        has_receipt_email=True,
    )
    try:
        payment = await asyncio.to_thread(
            create_yookassa_payment_with_receipt,
            shop_id=base.settings.yookassa_shop_id or "",
            secret_key=base.settings.yookassa_secret_key or "",
            product=product,
            product_key=product_key,
            report_id=report_id,
            user_id=user_id,
            return_url=base.settings.webapp_url,
            receipt_email=receipt_email,
        )
    except payments.YooKassaPaymentError as exc:
        base.logger.exception("YOOKASSA_CREATE_FAILED: %s", exc.technical_reason)
        await base._track_event(
            update,
            "premium_yookassa_create_failed",
            product_key=product_key,
            report_id=report_id,
        )
        if "receipt" in exc.technical_reason.lower() or "чек" in exc.user_message.lower():
            await base._tracked_replace_callback_text(
                update,
                context,
                "ЮKassa отклонила настройки чека. Деньги не списаны. Администратору нужно проверить фискализацию магазина; повторное нажатие сейчас даст ту же ошибку.",
                reply_markup=_receipt_configuration_keyboard(base, product_key),
            )
            return
        await base._tracked_replace_callback_text(
            update,
            context,
            exc.user_message,
            reply_markup=base.payment_recovery_keyboard(product_key, report_id=report_id),
        )
        return

    if not payment.payment_id or not payment.confirmation_url:
        await base._tracked_replace_callback_text(
            update,
            context,
            "ЮKassa не вернула рабочую ссылку. Деньги не списаны — откройте оплату ещё раз через минуту.",
            reply_markup=base.payment_recovery_keyboard(product_key, report_id=report_id),
        )
        return

    await asyncio.to_thread(
        save_checkout_session,
        base.get_store(),
        user_id,
        product_key,
        report_id,
        payment.payment_id,
        payment.confirmation_url,
    )

    context.user_data[base.PENDING_YOOKASSA_PAYMENT] = {
        "payment_id": payment.payment_id,
        "product_key": product_key,
        "report_id": report_id,
    }
    await base._tracked_replace_callback_text(
        update,
        context,
        (
            f"🧾 Ссылка на оплату готова\n\n"
            f"{product.title}\n"
            f"Сумма: {product.rubles} ₽\n"
            f"Чек придёт на {_masked_email(receipt_email)}.\n\n"
            "1. Откройте ЮKassa и завершите оплату.\n"
            "2. Вернитесь в бот и нажмите «Проверить оплату».\n\n"
            "Разбор уже сохранён и не исчезнет, даже если вы закроете страницу банка."
        ),
        reply_markup=base.yookassa_payment_keyboard(
            product_key,
            payment.payment_id,
            payment.confirmation_url,
            report_id,
        ),
    )


async def _reuse_checkout_if_possible(
    base: Any,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    *,
    product_key: str,
    report_id: int,
    user_id: int,
) -> bool:
    store = base.get_store()
    session = await asyncio.to_thread(get_checkout_session, store, user_id, product_key, report_id)
    if not session:
        return False

    payment_id = session.get("payment_id", "")
    confirmation_url = session.get("confirmation_url", "")
    if not payment_id or not payments._is_valid_confirmation_url(confirmation_url):
        await asyncio.to_thread(delete_checkout_session, store, user_id, product_key, report_id)
        return False

    try:
        payment = await asyncio.to_thread(
            payments.get_yookassa_payment,
            shop_id=base.settings.yookassa_shop_id or "",
            secret_key=base.settings.yookassa_secret_key or "",
            payment_id=payment_id,
        )
    except payments.YooKassaPaymentError:
        payment = None

    if payment is not None and payment.paid and payment.status == "succeeded":
        await asyncio.to_thread(store.grant_entitlement, user_id, product_key, report_id, payment_id)
        await base._track_event(
            update,
            "premium_repeat_purchase_blocked",
            product_key=product_key,
            report_id=report_id,
            reason="payment_already_succeeded",
        )
        await base._tracked_replace_callback_text(
            update,
            context,
            "Оплата уже подтверждена, доступ к этому материалу открыт. Повторно платить не нужно.",
            reply_markup=base.compact_planets_keyboard(report_id)
            if product_key in base.PLANET_PAYWALL_COPY
            else base.after_bridge_keyboard(report_id),
        )
        return True

    if payment is not None and payment.status not in {"pending", "waiting_for_capture"}:
        await asyncio.to_thread(delete_checkout_session, store, user_id, product_key, report_id)
        return False

    context.user_data[base.PENDING_YOOKASSA_PAYMENT] = {
        "payment_id": payment_id,
        "product_key": product_key,
        "report_id": report_id,
    }
    product = payments.get_product(product_key)
    await base._track_event(
        update,
        "premium_yookassa_payment_reused",
        product_key=product_key,
        report_id=report_id,
    )
    await base._tracked_replace_callback_text(
        update,
        context,
        (
            "Ссылка на эту покупку уже создана. Используйте её — второй платёж создавать не нужно."
            if product is None
            else f"Ссылка на оплату {product.title} уже создана. Используйте её — второй платёж не нужен."
        ),
        reply_markup=base.yookassa_payment_keyboard(
            product_key,
            payment_id,
            confirmation_url,
            report_id,
        ),
    )
    return True


def install(base: Any) -> None:
    original_premium_buy = base.premium_buy
    original_unknown_text = base.unknown_text
    original_premium_offer = base.premium_offer
    original_clear_flow_state = base._clear_flow_state

    def clear_payment_email_state(context: ContextTypes.DEFAULT_TYPE) -> None:
        context.user_data.pop(PENDING_RECEIPT_PRODUCT, None)
        context.user_data.pop(PENDING_RECEIPT_REPORT_ID, None)

    def clear_flow_state(context: ContextTypes.DEFAULT_TYPE) -> None:
        original_clear_flow_state(context)
        clear_payment_email_state(context)

    async def premium_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        raw_data = update.callback_query.data if update.callback_query else ""
        data, _ = base._callback_report(raw_data)
        if data == "premium:back":
            clear_payment_email_state(context)
        await original_premium_offer(update, context)

    async def premium_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not base.settings.yookassa_enabled:
            await original_premium_buy(update, context)
            return

        query = update.callback_query
        if query:
            await query.answer()
        await base._remember_user(update)
        raw_data = query.data if query else ""
        action, requested_report_id = base._callback_report(raw_data)
        if requested_report_id and not await base._activate_report_context(update, context, requested_report_id):
            await base._tracked_reply_text(
                update,
                context,
                "Эта кнопка относится к недоступному разбору. Откройте нужную карту через историю.",
                reply_markup=base.menu(),
            )
            return
        product_key = action.replace("premium:buy:", "")
        product = payments.get_product(product_key)
        report_id = base._current_report_id(context)
        user_id = base._user_id(update)
        if product is None or report_id <= 0 or user_id is None:
            await base._tracked_reply_text(
                update,
                context,
                "Сначала соберите разбор пары — тогда покупка будет привязана к нужной карте.",
                reply_markup=base.after_free_keyboard(),
            )
            return

        async with _checkout_lock(user_id, product_key, report_id):
            if await base._has_premium_access(update, context, product_key, report_id):
                await base._track_event(
                    update,
                    "premium_repeat_purchase_blocked",
                    product_key=product_key,
                    report_id=report_id,
                    reason="entitlement_exists",
                )
                await base._tracked_replace_callback_text(
                    update,
                    context,
                    "Этот материал уже куплен для этой карты — повторно платить не нужно.",
                    reply_markup=base.compact_planets_keyboard(report_id)
                    if product_key in base.PLANET_PAYWALL_COPY
                    else base.after_bridge_keyboard(report_id),
                )
                return

            if await _reuse_checkout_if_possible(
                base,
                update,
                context,
                product_key=product_key,
                report_id=report_id,
                user_id=user_id,
            ):
                return

            receipt_email = await asyncio.to_thread(get_receipt_email, base.get_store(), user_id)
            if not receipt_email:
                context.user_data[PENDING_RECEIPT_PRODUCT] = product_key
                context.user_data[PENDING_RECEIPT_REPORT_ID] = report_id
                await base._track_event(
                    update,
                    "receipt_email_requested",
                    product_key=product_key,
                    report_id=report_id,
                )
                await base._tracked_replace_callback_text(
                    update,
                    context,
                    (
                        "🧾 Для оплаты нужен email для электронного чека.\n\n"
                        "Отправьте его следующим сообщением, например name@yandex.ru. "
                        "ЮKassa пришлёт туда чек, а бот сохранит адрес для следующих покупок, чтобы больше не спрашивать.\n\n"
                        "Сам чек обязателен для этого магазина; без email ЮKassa не создаёт платёж."
                    ),
                    reply_markup=_email_prompt_keyboard(),
                )
                return

            await _open_yookassa_checkout(
                base,
                update,
                context,
                product_key=product_key,
                report_id=report_id,
                user_id=user_id,
                receipt_email=receipt_email,
            )

    async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        product_key = str(context.user_data.get(PENDING_RECEIPT_PRODUCT, ""))
        if not product_key:
            await original_unknown_text(update, context)
            return

        user_id = base._user_id(update)
        if user_id is None:
            clear_payment_email_state(context)
            return
        try:
            receipt_email = normalize_receipt_email((update.effective_message.text or "").strip())
        except ValueError as exc:
            await base._tracked_reply_text(
                update,
                context,
                f"{exc}\n\nEmail нужен только для электронного чека.",
                reply_markup=_email_prompt_keyboard(),
            )
            return

        report_id_raw = context.user_data.get(PENDING_RECEIPT_REPORT_ID, base._current_report_id(context))
        try:
            report_id = int(report_id_raw)
        except (TypeError, ValueError):
            report_id = 0
        await asyncio.to_thread(save_receipt_email, base.get_store(), user_id, receipt_email)
        clear_payment_email_state(context)
        await base._track_event(
            update,
            "receipt_email_saved",
            product_key=product_key,
            report_id=report_id,
        )
        async with _checkout_lock(user_id, product_key, report_id):
            if await base._has_premium_access(update, context, product_key, report_id):
                await base._tracked_reply_text(
                    update,
                    context,
                    "Этот материал уже куплен для этой карты — повторно платить не нужно.",
                    reply_markup=base.compact_planets_keyboard(report_id)
                    if product_key in base.PLANET_PAYWALL_COPY
                    else base.after_bridge_keyboard(report_id),
                )
                return
            if await _reuse_checkout_if_possible(
                base,
                update,
                context,
                product_key=product_key,
                report_id=report_id,
                user_id=user_id,
            ):
                return
            await _open_yookassa_checkout(
                base,
                update,
                context,
                product_key=product_key,
                report_id=report_id,
                user_id=user_id,
                receipt_email=receipt_email,
            )

    base._clear_flow_state = clear_flow_state
    base.premium_offer = premium_offer
    base.premium_buy = premium_buy
    base.unknown_text = unknown_text
