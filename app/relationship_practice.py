from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.astro.calculator import calculate_moon_confidence, calculate_placement
from app.astro.zodiac import angular_distance


@dataclass(frozen=True)
class DailyConnectionCard:
    title: str
    why: str
    action: str
    phrase: str
    reflection: str


@dataclass(frozen=True)
class WeeklyCoupleRitual:
    title: str
    why: str
    questions: tuple[str, str, str]
    gratitude: str
    request: str
    shared_plan: str
    challenge: str
    video_prompt: str
    safety_note: str


@dataclass(frozen=True)
class StarGoal:
    title: str
    sky_focus: str
    goal: str
    date_idea: str
    couple_challenge: str
    reflection: str
    safety_note: str


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


def _safe_timezone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def get_daily_connection_card(user_id: int | None, timezone_name: str) -> DailyConnectionCard:
    today = datetime.now(_safe_timezone(timezone_name)).date()
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


WEEKLY_COUPLE_RITUALS: tuple[WeeklyCoupleRitual, ...] = (
    WeeklyCoupleRitual(
        title="Неделя маленькой команды",
        why="Общая маленькая цель переводит пару из режима выяснений в режим 'мы вместе справляемся'.",
        questions=(
            "Что на этой неделе тебя поддержало во мне?",
            "Где тебе было со мной сложно, но ты хочешь сказать бережно?",
            "Какой один маленький шаг сделает следующую неделю теплее?",
        ),
        gratitude="Скажи одну конкретную благодарность за поступок, а не за 'всё'.",
        request="Попроси одну выполнимую вещь на неделю: время, помощь, тон, договорённость или паузу.",
        shared_plan="Выберите один общий план до 60 минут: прогулка, ужин, спорт, фильм без телефонов или бытовая задача вместе.",
        challenge="7 дней отмечать по одному хорошему моменту дня и отправлять друг другу короткое сообщение вечером.",
        video_prompt="Снимите 15-секундное видео 'наш маленький итог недели': один кадр, одна улыбка, одна фраза без идеальности.",
        safety_note="Если разговор уходит в давление, унижение или страх — ритуал останавливаем. Сначала безопасность и спокойствие.",
    ),
    WeeklyCoupleRitual(
        title="Неделя нового общего опыта",
        why="Новизна и совместное действие дают паре свежую энергию без тяжёлого разбора отношений.",
        questions=(
            "Что мы давно хотели попробовать, но откладывали?",
            "Какой формат будет приятным обоим, а не только одному?",
            "Что сделаем проще, чтобы точно не сорваться?",
        ),
        gratitude="Поблагодари за готовность пробовать новое, даже если результат будет несовершенным.",
        request="Попроси партнёра выбрать один вариант из двух, чтобы не превращать план в бесконечное обсуждение.",
        shared_plan="Запланируйте микро-приключение: новый маршрут, новое кафе, совместная тренировка, маленькая поездка или домашний квест.",
        challenge="Собрать 5 коротких видео или фото 'мы пробуем новое' и в конце недели выбрать самый живой момент.",
        video_prompt="Снимите короткий ролик 'до/после': ожидание перед планом и одна честная эмоция после.",
        safety_note="Челлендж не должен быть проверкой любви. Если кто-то устал, уменьшите масштаб, а не давите.",
    ),
    WeeklyCoupleRitual(
        title="Неделя преодоления без героизма",
        why="Пара крепнет не от драматичных подвигов, а от опыта: мы можем решить маленькую трудность без нападения друг на друга.",
        questions=(
            "Какая маленькая сложность у нас повторяется чаще всего?",
            "Что каждый из нас может сделать на 10% спокойнее?",
            "Как поймём, что на этой неделе стало легче?",
        ),
        gratitude="Отметь одну попытку партнёра, даже если она была неидеальной.",
        request="Сформулируй просьбу как эксперимент на 7 дней: 'давай попробуем вот так и посмотрим'.",
        shared_plan="Выберите одну бытовую или эмоциональную задачу и договоритесь о самом маленьком следующем шаге.",
        challenge="7-дневный челлендж 'без обобщений': не использовать в споре слова 'всегда', 'никогда', 'опять'.",
        video_prompt="Если комфортно обоим, снимите приватный ролик 'что мы улучшили на 1%' — не для публикации, а для памяти пары.",
        safety_note="Не берите челленджи на темы, где есть страх, контроль или принуждение. Там нужна поддержка, а не игра.",
    ),
)


def get_weekly_couple_ritual(user_id: int | None, timezone_name: str) -> WeeklyCoupleRitual:
    today = datetime.now(_safe_timezone(timezone_name)).date()
    _, week_number, _ = today.isocalendar()
    stable_user_shift = 0 if user_id is None else user_id % len(WEEKLY_COUPLE_RITUALS)
    index = (today.year + week_number + stable_user_shift) % len(WEEKLY_COUPLE_RITUALS)
    return WEEKLY_COUPLE_RITUALS[index]


def format_weekly_couple_ritual(ritual: WeeklyCoupleRitual) -> str:
    questions = "\n".join(f"{index}. {question}" for index, question in enumerate(ritual.questions, start=1))
    return (
        f"💞 Недельный ритуал пары\n\n"
        f"{ritual.title}\n\n"
        f"Зачем: {ritual.why}\n\n"
        f"3 вопроса друг другу:\n{questions}\n\n"
        f"1 благодарность: {ritual.gratitude}\n\n"
        f"1 просьба на неделю: {ritual.request}\n\n"
        f"1 общий план: {ritual.shared_plan}\n\n"
        f"Общий вызов: {ritual.challenge}\n\n"
        f"Видео-идея: {ritual.video_prompt}\n\n"
        f"Важно: {ritual.safety_note}"
    )


ELEMENT_STAR_GOALS: dict[str, tuple[str, str, str]] = {
    "fire": (
        "добавить живости без давления",
        "сделайте что-то динамичное: прогулка быстрым шагом, танец дома, спонтанный маршрут или короткая тренировка",
        "челлендж на день: каждый предлагает по одной смелой, но маленькой идее и выбирает одну общую",
    ),
    "earth": (
        "создать ощущение надёжности и тела",
        "сделайте уютный практичный план: ужин, порядок в одном уголке, массаж, тёплый чай или спокойная прогулка",
        "челлендж на день: закрыть одну маленькую бытовую задачу вместе и отметить результат",
    ),
    "air": (
        "вернуть разговор, лёгкость и интерес",
        "сходите туда, где можно говорить: кофе, книжный, выставка, прогулка с вопросами или вечер без тяжёлых тем",
        "челлендж на день: задать друг другу по 3 вопроса, на которые нельзя отвечать только 'да' или 'нет'",
    ),
    "water": (
        "дать больше мягкости, памяти и эмоциональной безопасности",
        "выберите тихий формат: фильм, ванна/чай, фото-воспоминания, спокойный разговор или место у воды",
        "челлендж на день: назвать один момент, где рядом с партнёром было тепло или спокойно",
    ),
}

MOON_PHASES: tuple[tuple[float, str, str], ...] = (
    (22.5, "новолуние", "начать маленький цикл: выбрать одну цель пары на ближайшие 7 дней"),
    (67.5, "растущая Луна", "добавить действие: не обсуждать бесконечно, а сделать первый маленький шаг"),
    (112.5, "первая четверть", "мягко преодолеть сопротивление: договориться об одном понятном правиле"),
    (157.5, "растущая к полнолунию", "прояснить ожидания до кульминации, пока эмоции не стали слишком громкими"),
    (202.5, "полнолуние", "увидеть кульминацию: что стало очевидным, что пора назвать честно и бережно"),
    (247.5, "убывающая Луна", "снять лишнее напряжение: убрать одну претензию и оставить одну просьбу"),
    (292.5, "последняя четверть", "пересобрать договорённость: что больше не работает и какой формат пробуем дальше"),
    (337.5, "бальзамическая Луна", "закрыть хвосты: извиниться, поблагодарить или отпустить одну мелкую обиду"),
    (360.0, "новолуние", "начать маленький цикл: выбрать одну цель пары на ближайшие 7 дней"),
)


def _today(timezone_name: str) -> date:
    return datetime.now(_safe_timezone(timezone_name)).date()


def _moon_phase_text(day: date) -> tuple[str, str]:
    sun = calculate_placement(day, "sun")
    moon = calculate_placement(day, "moon")
    distance = (moon.longitude - sun.longitude) % 360.0
    for limit, title, advice in MOON_PHASES:
        if distance < limit:
            return title, advice
    return MOON_PHASES[-1][1], MOON_PHASES[-1][2]


def get_star_goal(timezone_name: str) -> StarGoal:
    day = _today(timezone_name)
    moon = calculate_placement(day, "moon")
    venus = calculate_placement(day, "venus")
    mars = calculate_placement(day, "mars")
    moon_confidence = calculate_moon_confidence(day)
    phase_title, phase_advice = _moon_phase_text(day)
    goal, date_idea, challenge = ELEMENT_STAR_GOALS.get(moon.element, ELEMENT_STAR_GOALS["earth"])

    moon_event = f"Луна сегодня в знаке {moon.sign_ru}: фокус дня — {goal}."
    if moon_confidence.status == "changed_during_day":
        signs = ", ".join(item.sign_ru for item in moon_confidence.variants)
        moon_event = f"Луна сегодня меняет знак ({signs}): день лучше проживать гибко, без жёстких ожиданий."

    venus_angle = angular_distance(venus.longitude, mars.longitude)
    attraction_hint = (
        "добавьте инициативу и телесность" if venus_angle <= 60 else "лучше выбрать мягкий темп без проверки чувств"
    )

    return StarGoal(
        title="Звёздная цель дня",
        sky_focus=f"{moon_event} Фаза: {phase_title}. Венера в {venus.sign_ru}, Марс в {mars.sign_ru}: {attraction_hint}.",
        goal=f"Цель: {phase_advice}.",
        date_idea=f"Идея свидания: {date_idea}.",
        couple_challenge=f"Общий вызов: {challenge}.",
        reflection="Вечером спросите друг друга: что сегодня стало на 1% теплее, легче или честнее?",
        safety_note="Это не предсказание и не повод давить на партнёра. Используй как красивый повод к действию, а не как доказательство правоты.",
    )


def format_star_goal(goal: StarGoal) -> str:
    return (
        f"✨ {goal.title}\n\n"
        f"Что в небе: {goal.sky_focus}\n\n"
        f"{goal.goal}\n\n"
        f"{goal.date_idea}\n\n"
        f"{goal.couple_challenge}\n\n"
        f"Проверка пары: {goal.reflection}\n\n"
        f"Важно: {goal.safety_note}"
    )
