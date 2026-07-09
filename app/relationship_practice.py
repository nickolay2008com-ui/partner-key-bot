from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.astro.calculator import calculate_placement


@dataclass(frozen=True)
class DailyConnectionCard:
    title: str
    why: str
    action: str
    phrase: str
    reflection: str


DAILY_CONNECTION_CARDS: tuple[DailyConnectionCard, ...] = (
    DailyConnectionCard(
        title="Заметить маленький шаг навстречу",
        why="В отношениях часто работает не большой разговор, а маленький сигнал: я тебя вижу и не обесцениваю.",
        action="Сегодня отметь один конкретный поступок партнёра и поблагодари без намёка на долгий разговор.",
        phrase="Мне было приятно, что ты сделал это. Я заметила, спасибо.",
        reflection="После ответа оцени: стало теплее, нейтрально или напряжённее? Это поможет выбирать следующий шаг мягче.",
    ),
    DailyConnectionCard(
        title="Спросить без допроса",
        why="Спокойный вопрос снижает защиту лучше, чем претензия. Так появляется контакт, а не спор за правоту.",
        action="Задай один открытый вопрос и не исправляй ответ первые 2 минуты.",
        phrase="Как ты сегодня на самом деле? Я хочу просто понять, не спорить.",
        reflection="Если он коротко ответил, не добивай. Иногда первый безопасный шаг — оставить пространство.",
    ),
    DailyConnectionCard(
        title="Сказать потребность короче",
        why="Чем выше эмоция, тем важнее простая формулировка. Короткая просьба слышится легче, чем длинное объяснение боли.",
        action="Выбери одну потребность и скажи её одной фразой без обвинения.",
        phrase="Мне сейчас важно чуть больше тепла. Можешь просто обнять меня или написать пару слов?",
        reflection="Проверь, была ли просьба выполнимой прямо сегодня. Невыполнимая просьба часто превращается в конфликт.",
    ),
    DailyConnectionCard(
        title="Пауза перед острым сообщением",
        why="Пауза не подавляет чувства, а защищает отношения от фразы, которую потом придётся чинить.",
        action="Перед эмоциональным сообщением сделай 10 вдохов и убери из текста одно обобщение: «всегда», «никогда», «опять».",
        phrase="Я злюсь, но хочу сказать аккуратно: мне больно, когда мы резко обрываем разговор.",
        reflection="Если хочется доказать, кто прав, отложи отправку на 15 минут. Это забота о себе, не слабость.",
    ),
    DailyConnectionCard(
        title="Вернуть лёгкость",
        why="Близость держится не только на серьёзных разговорах. Лёгкий тёплый контакт помогает паре не жить только проблемами.",
        action="Отправь короткий добрый сигнал без требования ответа: воспоминание, шутку, фото или одну тёплую фразу.",
        phrase="Вспомнила наш момент и улыбнулась. Просто захотела тебе это сказать.",
        reflection="Если внутри есть обида, не используй лёгкость как маску. Сначала признай себе, что именно болит.",
    ),
    DailyConnectionCard(
        title="Маленькая договорённость",
        why="Отношениям помогают не идеальные обещания, а маленькие понятные договорённости, которые реально выполнить.",
        action="Предложи один конкретный ритуал на ближайшие сутки: 15 минут без телефонов, прогулку или спокойный звонок.",
        phrase="Давай сегодня 15 минут просто побудем вместе без телефонов? Без тяжёлых тем, просто рядом.",
        reflection="Хорошая договорённость звучит как приглашение, а не проверка любви.",
    ),
    DailyConnectionCard(
        title="Граница без холода",
        why="Тёплая граница сохраняет уважение к себе и не превращает разговор в наказание молчанием.",
        action="Если тебе неприятен тон или давление, назови границу и предложи безопасное продолжение позже.",
        phrase="Я хочу обсудить это, но не в резком тоне. Давай вернёмся к разговору, когда сможем говорить спокойнее.",
        reflection="Если есть страх, унижение, угрозы или контроль — это уже не про улучшение диалога. Важнее безопасность и поддержка.",
    ),
)

ELEMENT_GOALS: dict[str, str] = {
    "fire": "сделать один смелый, живой шаг навстречу без давления",
    "earth": "создать ощутимую заботу: еда, порядок, помощь, понятная договорённость",
    "air": "прояснить контакт словами: задать вопрос, пошутить, договориться легче",
    "water": "добавить эмоциональной безопасности: мягкий тон, принятие, бережную паузу",
}

MOON_PHASES: tuple[tuple[float, str, str], ...] = (
    (1.5, "Новолуние", "начинать мягко и не требовать быстрых ответов"),
    (6.5, "Растущая Луна", "наращивать контакт маленькими повторяемыми действиями"),
    (8.5, "Первая четверть", "выбрать один честный шаг вместо внутреннего спора"),
    (13.5, "Растущая почти полная Луна", "замечать эмоции до того, как они станут претензией"),
    (16.5, "Полнолуние", "снижать накал и не доказывать правоту через драму"),
    (21.5, "Убывающая Луна", "убирать лишнее напряжение и возвращать простоту"),
    (23.5, "Последняя четверть", "закрыть один хвост: извиниться, уточнить, договориться"),
    (29.6, "Старая Луна", "бережно завершать и отдыхать, не форсировать разговоры"),
)


def _safe_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def _today(timezone_name: str) -> date:
    return datetime.now(_safe_timezone(timezone_name)).date()


def _moon_phase(moon_longitude: float, sun_longitude: float) -> tuple[str, str, int]:
    synodic_month = 29.53058867
    elongation = (moon_longitude - sun_longitude) % 360.0
    age = elongation / 360.0 * synodic_month
    for limit, title, advice in MOON_PHASES:
        if age < limit:
            return title, advice, round(age)
    return MOON_PHASES[-1][1], MOON_PHASES[-1][2], round(age)


def get_daily_connection_card(user_id: int | None, timezone_name: str) -> DailyConnectionCard:
    today = _today(timezone_name)
    stable_user_shift = 0 if user_id is None else user_id % len(DAILY_CONNECTION_CARDS)
    index = (today.toordinal() + stable_user_shift) % len(DAILY_CONNECTION_CARDS)
    return DAILY_CONNECTION_CARDS[index]


def format_daily_connection_card(card: DailyConnectionCard) -> str:
    return (
        f"🔑 Сегодняшний ключ к контакту\n\n"
        f"{card.title}\n\n"
        f"Зачем: {card.why}\n\n"
        f"Что сделать: {card.action}\n\n"
        f"Фраза, если подходит:\n“{card.phrase}”\n\n"
        f"Проверка себя: {card.reflection}"
    )


def format_star_goal(timezone_name: str) -> str:
    today = _today(timezone_name)
    sun = calculate_placement(today, "sun")
    moon = calculate_placement(today, "moon")
    venus = calculate_placement(today, "venus")
    mars = calculate_placement(today, "mars")
    phase, phase_advice, age = _moon_phase(moon.longitude, sun.longitude)
    goal = ELEMENT_GOALS.get(moon.element, "сделать один бережный шаг к контакту")
    venus_hint = ELEMENT_GOALS.get(venus.element, "добавить тепла")
    mars_hint = ELEMENT_GOALS.get(mars.element, "действовать спокойно")
    return (
        "⭐️ Звёздная цель дня\n\n"
        f"Небо сегодня: Луна в {moon.sign_ru} ({moon.element_ru}), фаза — {phase}, примерно {age}-й лунный день. "
        f"Венера в {venus.sign_ru}, Марс в {mars.sign_ru}.\n\n"
        f"Цель: {goal}.\n\n"
        f"Как сделать: по Венере — {venus_hint}; по Марсу — {mars_hint}.\n\n"
        f"Ритм фазы: {phase_advice}.\n\n"
        "Важно: это не приговор и не аргумент в споре. Если в отношениях есть страх, контроль, угрозы или давление, цель дня — безопасность и поддержка, а не романтическая практика."
    )
