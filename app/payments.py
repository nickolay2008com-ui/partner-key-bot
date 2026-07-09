from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from telegram import LabeledPrice

CURRENCY_STARS = "XTR"
CURRENCY_RUB = "RUB"
PROVIDER_TOKEN_STARS = ""
YOOKASSA_API_URL = "https://api.yookassa.ru/v3/payments"


@dataclass(frozen=True)
class Product:
    key: str
    title: str
    description: str
    stars: int
    rubles: int

    @property
    def price(self) -> LabeledPrice:
        return LabeledPrice(label=self.title, amount=self.stars)

    @property
    def rub_amount(self) -> str:
        return f"{Decimal(self.rubles):.2f}"


@dataclass(frozen=True)
class YooKassaPayment:
    payment_id: str
    status: str
    confirmation_url: str | None = None
    paid: bool = False


PRODUCTS: dict[str, Product] = {
    "details": Product(
        "details",
        "Premium-карта пары",
        "Полная карта: эмоции, тепло, разговор, действие, рост и портреты в отношениях.",
        25,
        199,
    ),
    "message": Product(
        "message",
        "Premium-сообщение партнёру",
        "Три готовых варианта сообщения, тональность разговора и стоп-фраза.",
        15,
        149,
    ),
}


def get_product(key: str) -> Product | None:
    return PRODUCTS.get(key)


def make_payload(product_key: str, report_id: int) -> str:
    return f"pk:{product_key}:{report_id}"


def parse_payload(payload: str) -> tuple[str, int] | None:
    parts = payload.split(":")
    if len(parts) != 3 or parts[0] != "pk":
        return None
    product_key = parts[1]
    try:
        report_id = int(parts[2])
    except ValueError:
        return None
    if product_key not in PRODUCTS:
        return None
    return product_key, report_id


def _yookassa_request(shop_id: str, secret_key: str, method: str, url: str, body: dict | None = None) -> dict:
    credentials = base64.b64encode(f"{shop_id}:{secret_key}".encode("utf-8")).decode("ascii")
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Basic {credentials}",
        "Content-Type": "application/json",
    }
    if method == "POST":
        headers["Idempotence-Key"] = str(uuid.uuid4())
    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"YooKassa API error {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"YooKassa API unavailable: {exc.reason}") from exc


def create_yookassa_payment(
    *,
    shop_id: str,
    secret_key: str,
    product: Product,
    product_key: str,
    report_id: int,
    user_id: int,
    return_url: str,
) -> YooKassaPayment:
    payload = {
        "amount": {"value": product.rub_amount, "currency": CURRENCY_RUB},
        "capture": True,
        "confirmation": {"type": "redirect", "return_url": return_url},
        "description": f"{product.title} для отчёта #{report_id}",
        "metadata": {
            "product_key": product_key,
            "report_id": str(report_id),
            "telegram_user_id": str(user_id),
            "payload": make_payload(product_key, report_id),
        },
    }
    raw = _yookassa_request(shop_id, secret_key, "POST", YOOKASSA_API_URL, payload)
    confirmation = raw.get("confirmation") if isinstance(raw.get("confirmation"), dict) else {}
    return YooKassaPayment(
        payment_id=str(raw.get("id", "")),
        status=str(raw.get("status", "")),
        confirmation_url=confirmation.get("confirmation_url"),
        paid=bool(raw.get("paid")),
    )


def get_yookassa_payment(*, shop_id: str, secret_key: str, payment_id: str) -> YooKassaPayment:
    raw = _yookassa_request(shop_id, secret_key, "GET", f"{YOOKASSA_API_URL}/{payment_id}")
    confirmation = raw.get("confirmation") if isinstance(raw.get("confirmation"), dict) else {}
    return YooKassaPayment(
        payment_id=str(raw.get("id", payment_id)),
        status=str(raw.get("status", "")),
        confirmation_url=confirmation.get("confirmation_url"),
        paid=bool(raw.get("paid")),
    )
