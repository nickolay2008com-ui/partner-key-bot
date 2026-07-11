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


@dataclass(frozen=True)
class StarGoalPractice:
    focus: str
    why: str
    action: str
    phrase: str
    prosperity: str


STAR_GOAL_PRACTICES: dict[str, StarGoalPractice] = {
    "fire": StarGoalPractice(
        focus="добавить живой инициативы бережно",
        why="паре важно чувствовать интерес, радость и желание выбирать друг друга, а не только решать быт",
        action="сделай один тёплый заметный жест: комплимент, приглашение, короткое сообщение или совместный план",
        phrase="Мне хочется сегодня добавить нам тепла. Давай сделаем что-то приятное вместе?",
        prosperity="смелее предлагайте идеи и поддерживайте то, что зажигает энергию пары",
    ),
    "earth": StarGoalPractice(
        focus="показать заботу делом",
        why="доверие растёт, когда любовь становится ощутимой: помощь, порядок, еда, деньги, понятные договорённости",
        action="выбери одну практическую вещь и доведи до конца: помочь, убрать, приготовить, закрыть бытовой хвост или договориться о плане",
        phrase="Хочу сегодня облегчить нам день. Что одно я могу сделать, чтобы стало спокойнее?",
        prosperity="укрепляйте стабильность пары через бюджет, быт, здоровье и маленькие повторяемые улучшения",
    ),
    "air": StarGoalPractice(
        focus="прояснить словами, но не превращать разговор в спор",
        why="понимание появляется, когда люди задают вопросы, слышат ответы и договариваются простым языком",
        action="задай один спокойный вопрос, выслушай ответ и договорись о следующем маленьком шаге",
        phrase="Я хочу лучше тебя понять, не спорить. Как тебе было бы удобнее решить это сегодня?",
        prosperity="фиксируйте договорённости словами: кто что делает, когда возвращаетесь к теме, какой следующий шаг",
    ),
    "water": StarGoalPractice(
        focus="создать эмоциональную безопасность",
        why="близость крепнет, когда рядом можно чувствовать, не защищаться и не бояться резкой реакции",
        action="смягчи тон, назови чувство без обвинения и предложи паузу или поддержку",
        phrase="Мне важно быть с тобой в контакте. Давай поговорим мягко и без нападения?",
        prosperity="берегите эмоциональный климат: меньше проверок и драм, больше поддержки, отдыха и доверия",
    ),
}


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
        action="Если тебе неприятен тон или напор, назови границу и предложи безопасное продолжение позже.",
        phrase="Я хочу обсудить это, но не в резком тоне. Давай вернёмся к разговору, когда сможем говорить спокойнее.",
        reflection="Если есть страх, унижение, угрозы или контроль — это уже не про улучшение диалога. Важнее безопасность и поддержка.",
    ),
)

ELEMENT_GOALS: dict[str, str] = {
    "fire": "сделать один смелый, живой шаг навстречу бережно",
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


def format_daily_broadcast_card(card: DailyConnectionCard, day: date) -> str:
    date_label = day.strftime("%d.%m.%Y")
    return (
        f"🔑 Ключ к контакту на сегодня — {date_label}\n\n"
        f"{card.title}\n\n"
        f"Почему это важно: {card.why}\n\n"
        f"Мини-действие на 24 часа: {card.action}\n\n"
        f"Готовая мягкая фраза:\n“{card.phrase}”\n\n"
        f"Как понять, что сработало: {card.reflection}\n\n"
        "Если хочется точнее — сделайте разбор пары: /partner"
    )


def format_daily_broadcast_key(timezone_name: str, day: date | None = None) -> str:
    actual_day = day or _today(timezone_name)
    index = actual_day.toordinal() % len(DAILY_CONNECTION_CARDS)
    return format_daily_broadcast_card(DAILY_CONNECTION_CARDS[index], actual_day)


def format_star_goal(timezone_name: str) -> str:
    today = _today(timezone_name)
    sun = calculate_placement(today, "sun")
    moon = calculate_placement(today, "moon")
    venus = calculate_placement(today, "venus")
    mars = calculate_placement(today, "mars")
    phase, phase_advice, age = _moon_phase(moon.longitude, sun.longitude)
    practice = STAR_GOAL_PRACTICES.get(
        moon.element,
        StarGoalPractice(
            focus="сделать один бережный шаг к контакту",
            why="отношениям помогает не идеальная теория, а понятное действие, после которого рядом спокойнее",
            action="выбери один маленький шаг: спросить, помочь, обнять, договориться или дать паузу",
            phrase="Что сегодня поможет нам быть ближе и спокойнее?",
            prosperity="ищите один реальный шаг, который улучшает качество жизни пары уже сегодня",
        ),
    )
    venus_hint = ELEMENT_GOALS.get(venus.element, "добавить тепла")
    mars_hint = ELEMENT_GOALS.get(mars.element, "действовать спокойно")
    return (
        "⭐️ Звёздная цель дня\n\n"
        f"Главное: {practice.focus}.\n\n"
        f"Зачем паре: {practice.why}.\n\n"
        f"Что сделать сегодня: {practice.action}.\n\n"
        f"Фраза, если подходит:\n“{practice.phrase}”\n\n"
        f"Для процветания пары: {practice.prosperity}.\n\n"
        f"Ритм дня: {phase_advice}.\n\n"
        f"Астро-детали коротко: Луна в {moon.sign_ru} ({moon.element_ru}), {phase}, примерно {age}-й лунный день; "
        f"Венера — {venus_hint}; Марс — {mars_hint}.\n\n"
        "Важно: это подсказка для практики, а не приговор и не аргумент в споре. "
        "Если есть страх, контроль, угрозы или напор — главный шаг дня: безопасность и поддержка."
    )
