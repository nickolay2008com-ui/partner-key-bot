from __future__ import annotations

from dataclasses import dataclass

from telegram import LabeledPrice

CURRENCY_STARS = "XTR"
PROVIDER_TOKEN_STARS = ""


@dataclass(frozen=True)
class Product:
    key: str
    title: str
    description: str
    stars: int

    @property
    def price(self) -> LabeledPrice:
        return LabeledPrice(label=self.title, amount=self.stars)


PRODUCTS: dict[str, Product] = {
    "details": Product("details", "Глубокий ключ к партнёру", "Полный разбор: эмоции, симпатия, стиль общения и первый шаг.", 15),
    "message": Product("message", "Что написать партнёру", "Три мягких варианта сообщения под эмоциональный язык партнёра.", 10),
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
