from __future__ import annotations

import threading
import time
from typing import Any

from app import ad_attribution

_INSTALLED = False


def enqueue_conversion(
    base: Any,
    *,
    user_id: int,
    target: str,
    properties: dict[str, Any] | None = None,
    attribution: dict[str, Any] | None = None,
) -> bool:
    attribution = attribution or ad_attribution.get_store().latest_for_user(user_id)
    if not attribution:
        return False

    yclid = str(attribution.get("yclid") or "")
    token = str(attribution.get("token") or "")
    if not yclid or not token:
        return False

    properties = properties or {}
    product_key = str(properties.get("product_key") or "")
    report_id = str(properties.get("report_id") or "")

    event_key = f"{target}:{user_id}:{token}"
    if target in {"payment_started", "purchase_success"}:
        event_key += f":{report_id}:{product_key}"

    price: float | None = None
    currency: str | None = None
    # Доход передаём только после подтверждённой оплаты. Начало оплаты не является выручкой.
    if target == "purchase_success" and product_key:
        product = base.get_product(product_key)
        if product is not None:
            price = float(product.rubles)
            currency = "RUB"

    inserted = ad_attribution.get_store().enqueue(
        event_key=event_key,
        user_id=user_id,
        yclid=yclid,
        target=target,
        event_time=int(time.time()),
        price=price,
        currency=currency,
    )
    if inserted:
        threading.Thread(
            target=ad_attribution.flush_pending,
            name="metrica-offline-flush",
            daemon=True,
        ).start()
    return inserted


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ad_attribution.enqueue_conversion = enqueue_conversion
    _INSTALLED = True
