from __future__ import annotations

from dataclasses import asdict, dataclass, field

from app.astro.calculator import PartnerChart, Placement
from app.astro.meanings import (
    MARS_MEANINGS,
    MARS_SIGN_DETAILS,
    MERCURY_MEANINGS,
    MERCURY_SIGN_DETAILS,
    MESSAGE_TEMPLATES,
    MOON_MEANINGS,
    MOON_SIGN_DETAILS,
    VENUS_MEANINGS,
    VENUS_SIGN_DETAILS,
)


MOON_RHYTHM = {
    "fire": "Его эмоциональный ритм — Огонь: живость, отклик, движение, интерес.\n\nТакой человек чаще раскрывается не через тяжёлую серьёзность и долгие выяснения, а через ощущение: рядом есть жизнь, искра, желание двигаться навстречу.\n\nЕму легче становиться ближе, когда контакт не теряет живость, не превращается в обязанность и остаётся тёплым.",
    "earth": "Его эмоциональный ритм — Земля: спокойствие, тело, надёжность, понятность.\n\nТакой человек чаще раскрывается не через вспышки и громкие признания, а через ощущение: рядом устойчиво, спокойно, можно расслабиться.\n\nЕму легче становиться ближе, когда контакт не качает из стороны в сторону, а становится тёплым и надёжным.",
    "air": "Его эмоциональный ритм — Воздух: разговор, лёгкость, ясность, пространство.\n\nТакой человек чаще раскрывается не через давление на глубину, а через ощущение: рядом можно говорить, думать, шутить, дышать и не быть зажатым.\n\nЕму легче становиться ближе, когда контакт не сжимает пространство, а оставляет место для живого обмена.",
    "water": "Его эмоциональный ритм — Вода: мягкость, чувство, принятие, безопасность.\n\nТакой человек чаще раскрывается не через прямой нажим и холодную логику, а через ощущение: меня чувствуют, меня не торопят, рядом можно быть уязвимым.\n\nЕму легче становиться ближе, когда слова звучат не только правильно, но и тепло.",
}


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
    return f"{label}: {placement.sign_ru}, стихия {placement.element_ru}"


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
    return f"{label} в {sign}, {element}"


def _rhythm_with_basis(report: PartnerReport, meaning_core: str) -> str:
    rhythm = MOON_RHYTHM.get(report.emotional_language, meaning_core)
    basis = _report_basis(report, "moon", "Луна")
    marker = f"Его эмоциональный ритм — {report.emotional_language_title}:"
    replacement = f"Его эмоциональный ритм — {report.emotional_language_title} ({basis}):"
    if marker in rhythm:
        return rhythm.replace(marker, replacement, 1)
    return f"{rhythm}\n\nОснование: ({basis})"


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
    templates = MESSAGE_TEMPLATES[moon.element]
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

Главный вывод ({_placement_line("Луна", moon)}):
{name} легче раскрывается через язык: {moon.element_ru}.
{moon_meaning.core}{moon_note}

1. Эмоциональный язык ({_placement_line("Луна", moon)})
{moon_meaning.title}

Что человеку нужно:
{moon_meaning.needs}

Точный оттенок знака:
{moon_detail}

Как это обычно проявляется:
{moon_meaning.how_it_shows}

Как поддержать:
{moon_meaning.how_to_support}

Что лучше не делать:
{moon_meaning.what_not_to_do}

2. Как проявляется симпатия ({_placement_line("Венера", venus)})
{venus_text}

Точный оттенок знака:
{venus_detail}

3. Как говорить, чтобы вас услышали ({_placement_line("Меркурий", mercury)})
{mercury_text}

Точный оттенок знака:
{mercury_detail}

4. Как человек действует в напряжении ({_placement_line("Марс", mars)})
{mars_text}

Точный оттенок знака:
{mars_detail}

5. Как сделать хорошо обоим ({_placement_line("Луна", moon)})
{moon_meaning.bridge}

Первый шаг:
{moon_meaning.first_step}

Важно:
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
отношения становятся живее, когда человек чувствует ценность, вкус, удовольствие и естественное притяжение — не через давление, а через атмосферу, где ему приятно выбирать близость.

Как строить понимание ({mercury_basis}):
слова лучше работают, когда учитывают его способ мыслить, слышать и договариваться. Тогда разговор не разрушает связь, а возвращает ясность.

Как поддержать движение и процветание ({mars_basis}):
важно видеть, как человек действует, защищает границы и идёт к желаемому. Это помогает паре не тратить силу на борьбу темпов, а направлять энергию в общий рост.

Связь с отношениями и процветанием:
когда понятны спокойствие, ценность, слова и действие каждого, отношения становятся более наполненными: в них больше доверия, тепла, ясности и пространства для совместного процветания.
""".strip()


def format_free_preview(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    rhythm = _rhythm_with_basis(report, meaning.core)
    precision_note = format_moon_precision_note(report)
    precision_block = f"\n\n{precision_note}" if precision_note else ""
    basis = _report_basis(report, "moon", "Луна")
    return f"""
💞 Эмоциональный ритм мужчины: {report.partner_name}

{rhythm}{precision_block}

Основание описания: ({basis}).

Что может сбивать контакт ({basis}):
{meaning.what_not_to_do}

Мягкий ключ ({basis}):
{meaning.first_step}

Это не инструкция, как стать удобной. Это первый перевод его эмоционального ритма: в какой атмосфере ему легче расслабиться, доверять и быть ближе.

Дальше можно добавить вашу дату и увидеть уже не только его ритм, а ваш общий эмоциональный мост.
""".strip()


def format_message_templates(report: PartnerReport) -> str:
    lines = [f"✍️ Что можно написать: {report.partner_name}", ""]
    for index, template in enumerate(report.message_templates, start=1):
        lines.append(f"Вариант {index}:\n{template}")
        lines.append("")
    lines.append("Смысл не в том, чтобы давить. Смысл в том, чтобы говорить на языке, который человеку легче услышать.")
    return "\n".join(lines).strip()
