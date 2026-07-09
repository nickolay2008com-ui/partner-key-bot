from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SignInfo:
    key: str
    name_ru: str
    element: str
    element_ru: str


SIGNS: tuple[SignInfo, ...] = (
    SignInfo("aries", "Овен", "fire", "Огонь"),
    SignInfo("taurus", "Телец", "earth", "Земля"),
    SignInfo("gemini", "Близнецы", "air", "Воздух"),
    SignInfo("cancer", "Рак", "water", "Вода"),
    SignInfo("leo", "Лев", "fire", "Огонь"),
    SignInfo("virgo", "Дева", "earth", "Земля"),
    SignInfo("libra", "Весы", "air", "Воздух"),
    SignInfo("scorpio", "Скорпион", "water", "Вода"),
    SignInfo("sagittarius", "Стрелец", "fire", "Огонь"),
    SignInfo("capricorn", "Козерог", "earth", "Земля"),
    SignInfo("aquarius", "Водолей", "air", "Воздух"),
    SignInfo("pisces", "Рыбы", "water", "Вода"),
)

PLANET_NAMES_RU: dict[str, str] = {
    "sun": "Солнце",
    "moon": "Луна",
    "venus": "Венера",
    "mercury": "Меркурий",
    "mars": "Марс",
    "jupiter": "Юпитер",
}


def normalize_longitude(value: float) -> float:
    return value % 360.0


def sign_index(longitude: float) -> int:
    return int(normalize_longitude(longitude) // 30)


def sign_info(longitude: float) -> SignInfo:
    return SIGNS[sign_index(longitude)]


def angular_distance(a: float, b: float) -> float:
    """Smallest distance between two zodiac longitudes in degrees."""
    diff = abs(normalize_longitude(a) - normalize_longitude(b)) % 360.0
    return min(diff, 360.0 - diff)
