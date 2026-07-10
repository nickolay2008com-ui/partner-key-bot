from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.astro.calculator import PartnerChart, Placement
from app.astro.meanings import (
    MARS_MEANINGS,
    MARS_SIGN_DETAILS,
    MERCURY_MEANINGS,
    MERCURY_SIGN_DETAILS,
    MOON_MEANINGS,
    MOON_SIGN_DETAILS,
    VENUS_MEANINGS,
    VENUS_SIGN_DETAILS,
)


MOON_RHYTHM = {
    "fire": "Его эмоциональный ритм — Огонь: живость, отклик, движение, интерес.\n\nТакой человек чаще раскрывается не через тяжёлую серьёзность и долгие выяснения, а через ощущение: рядом есть жизнь, искра, желание двигаться навстречу.\n\nЕму легче становиться ближе, когда контакт не теряет живость, не превращается в обязанность и остаётся тёплым.",
    "earth": "Его эмоциональный ритм — Земля: спокойствие, тело, надёжность, понятность.\n\nТакой человек чаще раскрывается не через вспышки и громкие признания, а через ощущение: рядом устойчиво, спокойно, можно расслабиться.\n\nЕму легче становиться ближе, когда контакт не качает из стороны в сторону, а становится тёплым и надёжным.",
    "air": "Его эмоциональный ритм — Воздух: разговор, лёгкость, ясность, пространство.\n\nТакой человек чаще раскрывается не через напор на глубину, а через ощущение: рядом можно говорить, думать, шутить, дышать и не быть зажатым.\n\nЕму легче становиться ближе, когда контакт не сжимает пространство, а оставляет место для живого обмена.",
    "water": "Его эмоциональный ритм — Вода: мягкость, чувство, принятие, безопасность.\n\nТакой человек чаще раскрывается не через прямой нажим и холодную логику, а через ощущение: меня чувствуют, меня не торопят, рядом можно быть уязвимым.\n\nЕму легче становиться ближе, когда слова звучат не только правильно, но и тепло.",
}


PLANET_UNDERSTANDING = {
    "moon": "Луна показывает эмоциональную безопасность: где человек расслабляется, как просит заботу и в каком ритме начинает доверять.",
    "venus": "Венера показывает притяжение и ценность: что человеку красиво, приятно, желанно и через что он чувствует симпатию.",
    "mercury": "Меркурий показывает язык контакта: как человек думает, слышит слова, объясняет чувства и договаривается.",
    "mars": "Марс показывает действие и напряжение: как человек идёт к желаемому, защищается, спорит и возвращает себе силу.",
}


BEST_FLOW = {
    "moon": "Лучший ход событий — сначала дать безопасный ритм, потом тепло и только после этого ждать большей открытости.",
    "venus": "Лучший ход событий — не доказывать ценность, а создать состояние, в котором рядом с вами приятно, понятно и хочется повторения.",
    "mercury": "Лучший ход событий — говорить так, чтобы человеку было не страшно отвечать: коротко, честно, в его темпе и без игры в угадайку.",
    "mars": "Лучший ход событий — не разгонять конфликт, а дать энергии понятный выход: действие, решение, паузу или честное прояснение.",
}


PRACTICAL_KEYS = {
    "moon": "Практический ключ: наблюдай не только слова, а то, после чего человек становится мягче, спокойнее и ближе.",
    "venus": "Практический ключ: усиливай тот формат внимания, после которого у человека появляется интерес, вкус к контакту и желание быть рядом.",
    "mercury": "Практический ключ: выбирай формулировки, которые сохраняют достоинство обоих и сразу ведут к следующему понятному шагу.",
    "mars": "Практический ключ: в напряжении важнее не победить, а направить силу так, чтобы контакт не разрушился.",
}


ORIENTATION_KEY = (
    "🧭 Ориентация по карте: Луна задаёт эмоциональную дверь, Венера — способ притяжения, "
    "Меркурий — язык диалога, Марс — поведение в напряжении. Если соединить их мягко, "
    "карта становится не ярлыком, а понятной инструкцией: где дать тепло, где красоту, "
    "где слова, а где действие."
)


@dataclass(frozen=True)
class PartnerReport:
    partner_name: str
    birth_date: str
    moon_status: str
    emotional_language: str
    emotional_language_title: str
    placements: dict[str, dict[str, object]]
    summary: str
    text: str
    message_templates: list[str]
    moon_variants: list[dict[str, object]] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ReportContext:
    moon: Placement
    venus: Placement
    mercury: Placement
    mars: Placement


def _safe_name(name: str | None) -> str:
    cleaned = (name or "Партнёр").strip()
    return cleaned[:60] if cleaned else "Партнёр"


def _placement_line(label: str, placement: Placement) -> str:
    return f"{label}: {placement.sign_ru}, стихия {placement.element_ru}, {_placement_motion(placement)}"


def _main_moon_placement(chart: PartnerChart) -> Placement:
    return chart.placements["moon"]


def _placement_detail(placement: Placement, details: dict[str, str], fallback: str) -> str:
    return details.get(placement.sign_key, fallback)


def _variant_label(variant: dict[str, object]) -> str:
    sign = str(variant.get("sign_ru", "знак не определён"))
    element = str(variant.get("element_ru", "стихия не определена"))
    return f"{sign} ({element})"


def _report_placement(report: PartnerReport, key: str) -> dict[str, object]:
    value = report.placements.get(key)
    return value if isinstance(value, dict) else {}


def _report_basis(report: PartnerReport, key: str, label: str) -> str:
    placement = _report_placement(report, key)
    sign = str(placement.get("sign_ru", "знак не определён"))
    element = str(placement.get("element_ru", "стихия не определена"))
    return f"{label} в {sign}, {element}, {_report_motion(report, key)}"


def _placement_motion(placement: Placement) -> str:
    if placement.motion_status == "changed_during_day":
        return "смена движения в течение дня (без времени рождения возможны оба варианта)"
    return "ретроградное положение" if placement.is_retrograde else "прямое движение"


def _report_motion(report: PartnerReport, key: str) -> str:
    placement = _report_placement(report, key)
    if placement.get("motion_status") == "changed_during_day":
        return "смена движения в течение дня (без времени рождения возможны оба варианта)"
    return "ретроградное положение" if bool(placement.get("is_retrograde", False)) else "прямое движение"


def _retrograde_note_by_key(key: str, label: str, is_retrograde: bool, motion_status: str = "stable") -> str:
    if motion_status == "changed_during_day":
        return f"\n\n↩️ Точность ретроградности ({label}):\nВ этот день планета меняла направление. Без точного времени рождения нельзя честно выбрать один вариант, поэтому трактовку лучше читать как развилку: прямое движение даёт более внешнее проявление, ретроградное — более внутреннюю переработку темы."
    if not is_retrograde:
        return ""
    notes = {
        "mercury": "Ретроградность добавляет внутреннюю паузу в мышлении и словах: лучше оставлять время подумать, уточнять смысл и фиксировать договорённости спокойно.",
        "venus": "Ретроградность делает тему ценности и симпатии более внутренней: человеку может быть важно присмотреться, проверить доверие и не спешить с признаниями.",
        "mars": "Ретроградность разворачивает действие внутрь: энергия может копиться или идти рывками, поэтому лучше предлагать маленький понятный шаг бережно.",
        "jupiter": "Ретроградность показывает рост через личный смысл: человеку важно сначала внутренне поверить в горизонт, а потом расширяться наружу.",
    }
    text = notes.get(key, "Ретроградность делает проявление планеты более внутренним: сначала тема перерабатывается внутри, затем проявляется наружу.")
    return f"\n\n↩️ Ретроградность ({label}):\n{text}"


def _report_retrograde_note(report: PartnerReport, key: str, label: str) -> str:
    placement = _report_placement(report, key)
    return _retrograde_note_by_key(key, label, bool(placement.get("is_retrograde", False)), str(placement.get("motion_status", "stable")))


def _rhythm_without_placement_badge(report: PartnerReport, meaning_core: str) -> str:
    return MOON_RHYTHM.get(report.emotional_language, meaning_core)


def format_moon_precision_note(report: PartnerReport) -> str:
    if report.moon_status != "changed_during_day":
        return ""
    variants = " / ".join(_variant_label(item) for item in report.moon_variants) or "два соседних знака Луны"
    return (
        "⚠️ Точность Луны: в этот день Луна могла менять знак. "
        f"Возможные варианты: {variants}. Без времени рождения это ориентир по середине дня, "
        "а не окончательный астрологический вывод."
    )


def build_partner_report(chart: PartnerChart, partner_name: str | None = None) -> PartnerReport:
    name = _safe_name(partner_name)
    moon = _main_moon_placement(chart)
    venus = chart.placements["venus"]
    mercury = chart.placements["mercury"]
    mars = chart.placements["mars"]

    moon_meaning = MOON_MEANINGS[moon.element]
    moon_detail = _placement_detail(
        moon,
        MOON_SIGN_DETAILS,
        "Точный знак Луны уточняет, какой формат эмоционального спокойствия человеку ближе.",
    )
    venus_text = VENUS_MEANINGS[venus.element]
    venus_detail = _placement_detail(
        venus,
        VENUS_SIGN_DETAILS,
        "Точный знак Венеры уточняет, где у человека включаются ценность, вкус и притяжение.",
    )
    mercury_text = MERCURY_MEANINGS[mercury.element]
    mercury_detail = _placement_detail(
        mercury,
        MERCURY_SIGN_DETAILS,
        "Точный знак Меркурия уточняет, как человеку легче мыслить, слышать слова и договариваться.",
    )
    mars_text = MARS_MEANINGS[mars.element]
    mars_detail = _placement_detail(
        mars,
        MARS_SIGN_DETAILS,
        "Точный знак Марса уточняет, как человек движется, действует и защищает своё направление.",
    )
    templates: list[str] = []
    moon_variants = [item.to_dict() for item in chart.moon_confidence.variants]

    moon_note = ""
    if not chart.moon_confidence.is_exact_enough:
        variants = " / ".join(f"{item.sign_ru} ({item.element_ru})" for item in chart.moon_confidence.variants)
        moon_note = (
            "\n\n⚠️ Луна в этот день могла менять знак. "
            f"Возможные варианты: {variants}. Ниже я беру практическую середину дня, "
            "а точнее можно выбрать по описанию поведения."
        )

    text = f"""
🔑 Глубокий ключ к партнёру: {name}

Дата рождения: {chart.birth_date:%d.%m.%Y}

🌙 Главный вывод ({_placement_line("Луна", moon)}):
{name} легче раскрывается через язык: {moon.element_ru}.
{moon_meaning.core}{moon_note}

✨ Как читать эту карту
Сначала смотри, какую сферу несёт планета, потом — общий сценарий по стихии, затем точный оттенок знака. Так описание превращается не в абстрактную астрологию, а в понятный способ поведения.

1. 🌙 Луна — эмоциональная безопасность ({_placement_line("Луна", moon)})
Что несёт планета:
{PLANET_UNDERSTANDING["moon"]}

Общая интерпретация:
{moon_meaning.title}

Что человеку нужно:
{moon_meaning.needs}

Лучший ход событий:
{BEST_FLOW["moon"]}

Тональность с учётом знака:
{moon_detail}

Как это обычно проявляется:
{moon_meaning.how_it_shows}

Как поддержать:
{moon_meaning.how_to_support}

Практический ключ:
{PRACTICAL_KEYS["moon"]}

Что лучше не делать:
{moon_meaning.what_not_to_do}

2. 💗 Венера — симпатия, вкус и притяжение ({_placement_line("Венера", venus)})
Что несёт планета:
{PLANET_UNDERSTANDING["venus"]}

Общая интерпретация:
{venus_text}

Лучший ход событий:
{BEST_FLOW["venus"]}

Тональность с учётом знака:
{venus_detail}{_retrograde_note_by_key("venus", "Венера", venus.is_retrograde, venus.motion_status)}

Практический ключ:
{PRACTICAL_KEYS["venus"]}

3. 🗣️ Меркурий — слова, мышление и договорённости ({_placement_line("Меркурий", mercury)})
Что несёт планета:
{PLANET_UNDERSTANDING["mercury"]}

Общая интерпретация:
{mercury_text}

Лучший ход событий:
{BEST_FLOW["mercury"]}

Тональность с учётом знака:
{mercury_detail}{_retrograde_note_by_key("mercury", "Меркурий", mercury.is_retrograde, mercury.motion_status)}

Практический ключ:
{PRACTICAL_KEYS["mercury"]}

4. 🔥 Марс — действие, желание и напряжение ({_placement_line("Марс", mars)})
Что несёт планета:
{PLANET_UNDERSTANDING["mars"]}

Общая интерпретация:
{mars_text}

Лучший ход событий:
{BEST_FLOW["mars"]}

Тональность с учётом знака:
{mars_detail}{_retrograde_note_by_key("mars", "Марс", mars.is_retrograde, mars.motion_status)}

Практический ключ:
{PRACTICAL_KEYS["mars"]}

5. 🧩 Как соединить карту в понятное применение
{ORIENTATION_KEY}

Как сделать хорошо обоим ({_placement_line("Луна", moon)}):
{moon_meaning.bridge}

Первый шаг:
{moon_meaning.first_step}

📌 Важно:
Это не приговор отношениям и не проверка совместимости. Это профессиональная карта наблюдения: какие условия помогают человеку доверять, слышать и проявляться теплее.
""".strip()

    summary = f"{name}: эмоциональный язык — {moon.element_ru}. {moon_meaning.needs}"

    return PartnerReport(
        partner_name=name,
        birth_date=chart.birth_date.isoformat(),
        moon_status=chart.moon_confidence.status,
        emotional_language=moon.element,
        emotional_language_title=moon_meaning.title,
        placements={key: value.to_dict() for key, value in chart.placements.items()},
        summary=summary,
        text=text,
        message_templates=templates,
        moon_variants=moon_variants,
    )


def format_person_portrait(report: PartnerReport, heading: str | None = None) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    moon_basis = _report_basis(report, "moon", "Луна")
    venus_basis = _report_basis(report, "venus", "Венера")
    mercury_basis = _report_basis(report, "mercury", "Меркурий")
    mars_basis = _report_basis(report, "mars", "Марс")
    title = heading or f"👤 Портрет: {report.partner_name}"
    return f"""
{title}

Внутренняя опора ({moon_basis}):
{meaning.needs}

Как наполняется контакт ({venus_basis}):
отношения становятся живее, когда человек чувствует ценность, вкус, удовольствие и естественное притяжение — не через напор, а через атмосферу, где ему приятно выбирать близость.{_report_retrograde_note(report, "venus", "Венера")}

Как строить понимание ({mercury_basis}):
слова лучше работают, когда учитывают его способ мыслить, слышать и договариваться. Тогда разговор не разрушает связь, а возвращает ясность.{_report_retrograde_note(report, "mercury", "Меркурий")}

Как поддержать движение и процветание ({mars_basis}):
важно видеть, как человек действует, защищает границы и идёт к желаемому. Это помогает паре не тратить силу на борьбу темпов, а направлять энергию в общий рост.{_report_retrograde_note(report, "mars", "Марс")}

Связь с отношениями и процветанием:
когда понятны спокойствие, ценность, слова и действие каждого, отношения становятся более наполненными: в них больше доверия, тепла, ясности и пространства для совместного процветания.
""".strip()


def format_free_preview(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    rhythm = _rhythm_without_placement_badge(report, meaning.core)
    return f"""
💞 Эмоциональный ритм мужчины: {report.partner_name}

{rhythm}

Что может сбивать контакт:
{meaning.what_not_to_do}

Мягкий ключ:
{meaning.first_step}

Это не инструкция, как стать удобной. Это первый перевод его эмоционального ритма: в какой атмосфере ему легче расслабиться, доверять и быть ближе.

Дальше можно добавить вашу дату и увидеть уже не только его ритм, а ваш общий эмоциональный мост.
""".strip()


def format_message_guidance(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    moon_basis = _report_basis(report, "moon", "Луна")
    venus_basis = _report_basis(report, "venus", "Венера")
    mercury_basis = _report_basis(report, "mercury", "Меркурий")
    mars_basis = _report_basis(report, "mars", "Марс")

    return f"""
✍️ Что можно написать: общий ориентир для {report.partner_name}

Не нужен идеальный готовый текст. Лучше написать своими словами так, чтобы в сообщении были понятны смысл, цель и бережный тон.

Смысл сообщения:
показать, что контакт важен, но без проверок, обвинения или попытки получить гарантированный ответ.

Цель сообщения:
создать понятный следующий шаг: мягко прояснить контакт, предложить встречу/разговор или вернуть спокойный ритм общения.

На что опереться ({moon_basis}):
{meaning.needs}

Какой тон выбрать ({mercury_basis}):
говори так, чтобы человеку было легче ответить спокойно: коротко, ясно, без намёков, ультиматумов и эмоционального шантажа.{_report_retrograde_note(report, "mercury", "Меркурий")}

Что добавить для тепла ({venus_basis}):
немного ценности и приятности: не доказывать любовь, а дать ощущение, что рядом может быть спокойно, интересно и по-доброму.{_report_retrograde_note(report, "venus", "Венера")}

Как не разогнать напряжение ({mars_basis}):
если есть обида или пауза, не начинай с претензии. Лучше предложить маленькое действие: поговорить, встретиться, уточнить или взять паузу без холодности.{_report_retrograde_note(report, "mars", "Марс")}

Структура сообщения:
1. Тёплое признание: почему ты пишешь.
2. Один ясный смысл: что тебе важно.
3. Один спокойный следующий шаг: что предлагаешь.
4. Свобода ответа: без требования немедленной реакции.

Чего избегать:
{meaning.what_not_to_do}

Формула:
«Мне важно [смысл]. Я не хочу торопить события. Давай [один простой шаг], если тебе это тоже сейчас ок».

Главное: сообщение должно звучать живо и по-человечески, а не как скрипт. Смысл не в том, чтобы подобрать волшебную фразу, а в том, чтобы говорить на языке, который человеку легче услышать.
""".strip()
