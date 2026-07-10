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
    metadata: dict[str, str] | None = None

    @property
    def product_key(self) -> str:
        return (self.metadata or {}).get("product_key", "")

    @property
    def report_id(self) -> int:
        try:
            return int((self.metadata or {}).get("report_id", "0"))
        except ValueError:
            return 0

    @property
    def telegram_user_id(self) -> int:
        try:
            return int((self.metadata or {}).get("telegram_user_id", "0"))
        except ValueError:
            return 0


PRODUCTS: dict[str, Product] = {
    "details": Product(
        "details",
        "Premium-карта пары: глубокий разбор",
        "Сильная карта действий: эмоции, тепло, разговор, действие, рост и портреты — чтобы быстрее понять партнёра и выбрать следующий шаг.",
        25,
        199,
    ),
    "message": Product(
        "message",
        "Premium-сообщение: сильный первый шаг",
        "Три готовых сообщения, тональность разговора и стоп-фраза — чтобы написать увереннее, мягче и с большим шансом быть услышанной.",
        15,
        149,
    ),
    "planet_venus": Product(
        "planet_venus",
        "Венера пары: его разбор + ваша бесплатно",
        "Подробная Венера мужчины за 50 ₽ и ваша Венера бесплатно — чтобы понять, что включает нежность и притяжение в паре.",
        5,
        50,
    ),
    "planet_mercury": Product(
        "planet_mercury",
        "Меркурий пары: его разбор + ваш бесплатно",
        "Подробный Меркурий мужчины за 50 ₽ и ваш Меркурий бесплатно — чтобы говорить словами, которые легче услышать обоим.",
        5,
        50,
    ),
    "planet_mars": Product(
        "planet_mars",
        "Марс пары: его разбор + ваш бесплатно",
        "Подробный Марс мужчины за 50 ₽ и ваш Марс бесплатно — чтобы поддерживать действие без давления и борьбы.",
        5,
        50,
    ),
    "planet_jupiter": Product(
        "planet_jupiter",
        "Юпитер пары: его разбор + ваш бесплатно",
        "Подробный Юпитер мужчины за 50 ₽ и ваш Юпитер бесплатно — чтобы видеть общий горизонт роста и доверия.",
        5,
        50,
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
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return YooKassaPayment(
        payment_id=str(raw.get("id", "")),
        status=str(raw.get("status", "")),
        confirmation_url=confirmation.get("confirmation_url"),
        paid=bool(raw.get("paid")),
        metadata={str(key): str(value) for key, value in metadata.items()},
    )


def get_yookassa_payment(*, shop_id: str, secret_key: str, payment_id: str) -> YooKassaPayment:
    raw = _yookassa_request(shop_id, secret_key, "GET", f"{YOOKASSA_API_URL}/{payment_id}")
    confirmation = raw.get("confirmation") if isinstance(raw.get("confirmation"), dict) else {}
    metadata = raw.get("metadata") if isinstance(raw.get("metadata"), dict) else {}
    return YooKassaPayment(
        payment_id=str(raw.get("id", payment_id)),
        status=str(raw.get("status", "")),
        confirmation_url=confirmation.get("confirmation_url"),
        paid=bool(raw.get("paid")),
        metadata={str(key): str(value) for key, value in metadata.items()},
    )
