from __future__ import annotations

from dataclasses import asdict, dataclass

from app.astro.calculator import PartnerChart, Placement
from app.astro.meanings import MARS_MEANINGS, MERCURY_MEANINGS, MESSAGE_TEMPLATES, MOON_MEANINGS, VENUS_MEANINGS


MOON_ATMOSPHERE = {
    "fire": "Рядом с таким человеком тепло появляется как искра: через живость, отклик, интерес и ощущение, что контакт не погас. Ему важно чувствовать, что рядом есть жизнь, движение и внутренняя включённость.",
    "earth": "Рядом с таким человеком тепло появляется не вспышкой, а как свет в окне, который снова горит каждый вечер. Ему важно почувствовать устойчивость: здесь спокойно, здесь не дёргают, здесь можно постепенно стать ближе.",
    "air": "Рядом с таким человеком близость часто начинается с воздуха между вами: с фразы, взгляда, шутки, мысли, лёгкого движения разговора. Ему важно, чтобы контакт не становился клеткой и чтобы в нём оставалось пространство дышать.",
    "water": "Рядом с таким человеком многое живёт в полутонах. Он может чувствовать больше, чем говорит, и слышать не только слова, но и тон, паузу, настроение. Ему важно, чтобы рядом было бережно, не грубо и не холодно.",
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


def build_partner_report(chart: PartnerChart, partner_name: str | None = None) -> PartnerReport:
    name = _safe_name(partner_name)
    moon = _main_moon_placement(chart)
    venus = chart.placements["venus"]
    mercury = chart.placements["mercury"]
    mars = chart.placements["mars"]

    moon_meaning = MOON_MEANINGS[moon.element]
    venus_text = VENUS_MEANINGS[venus.element]
    mercury_text = MERCURY_MEANINGS[mercury.element]
    mars_text = MARS_MEANINGS[mars.element]
    templates = MESSAGE_TEMPLATES[moon.element]

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

Главный вывод:
{name} легче раскрывается через язык: {moon.element_ru}.
{moon_meaning.core}{moon_note}

1. Эмоциональный язык
{moon_meaning.title}

Что человеку нужно:
{moon_meaning.needs}

Как это обычно проявляется:
{moon_meaning.how_it_shows}

Как поддержать:
{moon_meaning.how_to_support}

Что лучше не делать:
{moon_meaning.what_not_to_do}

2. Как проявляется симпатия
{_placement_line("Венера", venus)}
{venus_text}

3. Как говорить, чтобы вас услышали
{_placement_line("Меркурий", mercury)}
{mercury_text}

4. Как человек действует в напряжении
{_placement_line("Марс", mars)}
{mars_text}

5. Как сделать хорошо обоим
{moon_meaning.bridge}

Первый шаг:
{moon_meaning.first_step}

Важно:
Это не приговор отношениям и не проверка совместимости. Это мягкая карта понимания: какие условия помогают человеку доверять, слышать и быть теплее.
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
    )


def format_free_preview(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    atmosphere = MOON_ATMOSPHERE.get(report.emotional_language, meaning.core)
    return f"""
💞 Эмоциональный ритм мужчины: {report.partner_name}

Его базовый язык: {meaning.title}

{atmosphere}

В этом нет инструкции, как стать удобной. Скорее это первый намёк на его внутренний климат: в какой атмосфере он меньше защищается и легче становится живым рядом.

Что может закрывать контакт:
{meaning.what_not_to_do}

Мягкий вход:
{meaning.first_step}

Дальше можно добавить вашу дату и увидеть уже не только его ритм, а ваш общий эмоциональный мост.
""".strip()


def format_message_templates(report: PartnerReport) -> str:
    lines = [f"✍️ Что можно написать: {report.partner_name}", ""]
    for index, template in enumerate(report.message_templates, start=1):
        lines.append(f"Вариант {index}:\n{template}")
        lines.append("")
    lines.append("Смысл не в том, чтобы давить. Смысл в том, чтобы говорить на языке, который человеку легче услышать.")
    return "\n".join(lines).strip()
