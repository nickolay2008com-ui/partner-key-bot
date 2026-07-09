from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import date

import swisseph as swe

from app.astro.zodiac import PLANET_NAMES_RU, sign_info

MIN_SUPPORTED_YEAR = 1900
MAX_SUPPORTED_YEAR = 2100
CALC_FLAGS = swe.FLG_MOSEPH

PLANET_IDS: dict[str, int] = {
    "sun": swe.SUN,
    "moon": swe.MOON,
    "venus": swe.VENUS,
    "mercury": swe.MERCURY,
    "mars": swe.MARS,
    "jupiter": swe.JUPITER,
}

DATE_PATTERNS: tuple[str, ...] = (
    r"(?P<day>\d{1,2})[.\-/](?P<month>\d{1,2})[.\-/](?P<year>\d{4})",
    r"(?P<year>\d{4})[.\-/](?P<month>\d{1,2})[.\-/](?P<day>\d{1,2})",
)


@dataclass(frozen=True)
class Placement:
    planet: str
    planet_ru: str
    longitude: float
    sign_key: str
    sign_ru: str
    element: str
    element_ru: str
    is_retrograde: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class MoonConfidence:
    status: str
    message: str
    variants: tuple[Placement, ...]

    @property
    def is_exact_enough(self) -> bool:
        return self.status == "stable"

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "message": self.message,
            "variants": [item.to_dict() for item in self.variants],
        }


@dataclass(frozen=True)
class PartnerChart:
    birth_date: date
    placements: dict[str, Placement]
    moon_confidence: MoonConfidence

    def to_dict(self) -> dict[str, object]:
        return {
            "birth_date": self.birth_date.isoformat(),
            "placements": {key: value.to_dict() for key, value in self.placements.items()},
            "moon_confidence": self.moon_confidence.to_dict(),
        }


def parse_birth_date(text: str) -> date:
    cleaned = text.strip()
    for pattern in DATE_PATTERNS:
        match = re.search(pattern, cleaned)
        if not match:
            continue
        parts = {key: int(value) for key, value in match.groupdict().items()}
        year = parts["year"]
        if year < MIN_SUPPORTED_YEAR or year > MAX_SUPPORTED_YEAR:
            raise ValueError(
                f"Проверь год рождения. Сейчас поддерживается диапазон {MIN_SUPPORTED_YEAR}–{MAX_SUPPORTED_YEAR}. Формат: 12.04.1993"
            )
        try:
            return date(year, parts["month"], parts["day"])
        except ValueError as exc:
            raise ValueError("Дата выглядит неверно. Формат: 12.04.1993") from exc
    raise ValueError("Не увидел дату. Напиши так: 12.04.1993")


def _julian_day(day: date, hour_utc: float) -> float:
    return swe.julday(day.year, day.month, day.day, hour_utc)


def calculate_placement(day: date, planet: str, hour_utc: float = 12.0) -> Placement:
    if planet not in PLANET_IDS:
        raise ValueError(f"Неизвестная планета: {planet}")
    jd = _julian_day(day, hour_utc)
    try:
        result, _flags = swe.calc_ut(jd, PLANET_IDS[planet], CALC_FLAGS)
    except Exception as exc:
        raise RuntimeError(
            "Не удалось посчитать карту. Попробуй другую дату или повтори чуть позже. Внутренняя ошибка расчёта уже спрятана, потому что пользователю не надо видеть кишки эфемерид."
        ) from exc
    longitude = float(result[0])
    speed_longitude = float(result[3])
    sign = sign_info(longitude)
    return Placement(
        planet=planet,
        planet_ru=PLANET_NAMES_RU.get(planet, planet),
        longitude=round(longitude, 6),
        sign_key=sign.key,
        sign_ru=sign.name_ru,
        element=sign.element,
        element_ru=sign.element_ru,
        is_retrograde=speed_longitude < 0,
    )


def calculate_moon_confidence(day: date) -> MoonConfidence:
    start = calculate_placement(day, "moon", hour_utc=0.0)
    end = calculate_placement(day, "moon", hour_utc=23.999)
    noon = calculate_placement(day, "moon", hour_utc=12.0)

    if start.sign_key == end.sign_key:
        return MoonConfidence(
            status="stable",
            message="Луна в этот день остаётся в одном знаке. Для MVP без времени рождения этого достаточно.",
            variants=(noon,),
        )

    variants: list[Placement] = []
    seen: set[str] = set()
    for item in (start, end):
        if item.sign_key not in seen:
            variants.append(item)
            seen.add(item.sign_key)

    return MoonConfidence(
        status="changed_during_day",
        message="В этот день Луна меняла знак. Без точного времени рождения лучше показать два варианта и выбрать похожий по поведению.",
        variants=tuple(variants),
    )


def calculate_partner_chart(day: date) -> PartnerChart:
    placements = {
        "moon": calculate_placement(day, "moon"),
        "venus": calculate_placement(day, "venus"),
        "mercury": calculate_placement(day, "mercury"),
        "mars": calculate_placement(day, "mars"),
        "jupiter": calculate_placement(day, "jupiter"),
    }
    moon_confidence = calculate_moon_confidence(day)
    if moon_confidence.is_exact_enough:
        placements["moon"] = moon_confidence.variants[0]
    return PartnerChart(birth_date=day, placements=placements, moon_confidence=moon_confidence)
