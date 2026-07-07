from __future__ import annotations

from dataclasses import asdict, dataclass

from app.astro.calculator import PartnerChart, Placement
from app.astro.meanings import MARS_MEANINGS, MERCURY_MEANINGS, MESSAGE_TEMPLATES, MOON_MEANINGS, VENUS_MEANINGS


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


MOON_SIGN_FOCUS: dict[str, str] = {
    "Овен": "ему хорошо, когда рядом есть живость, прямота, инициатива и ощущение, что жизнь движется, а не вязнет в бесконечных выяснениях.",
    "Телец": "ему хорошо через телесный комфорт, спокойствие, вкус, прикосновения, устойчивый ритм, уют и отсутствие резких качелей.",
    "Близнецы": "ему хорошо, когда можно говорить легко, шутить, обсуждать, менять тему и не чувствовать тяжёлое эмоциональное давление.",
    "Рак": "ему хорошо там, где есть нежность, дом, забота, память о деталях и чувство, что рядом можно быть мягким без защиты.",
    "Лев": "ему хорошо, когда его тепло замечают, уважают, вдохновляют и дают ощущение значимости без игры в унижение или холод.",
    "Дева": "ему хорошо через порядок, полезность, конкретную заботу, уважение к режиму и спокойную помощь без хаоса и драматизма.",
    "Весы": "ему хорошо в атмосфере красоты, такта, лёгкого диалога, уважения и мягкого равновесия без грубого давления.",
    "Скорпион": "ему хорошо, когда есть глубина, честность, доверие и отсутствие поверхностных игр, но без вторжения и контроля.",
    "Стрелец": "ему хорошо там, где есть свобода, движение, смысл, юмор, перспектива и ощущение, что рядом не сужают его мир.",
    "Козерог": "ему хорошо, когда рядом надёжно, спокойно, уважительно к целям и без требования постоянно доказывать чувства словами.",
    "Водолей": "ему хорошо, когда есть свобода, дружба, интерес, необычность, право быть собой и отсутствие эмоциональной клетки.",
    "Рыбы": "ему хорошо в мягкости, принятии, тонком чувстве, тишине, вдохновении и бережном контакте без грубой рационализации.",
}

BRIDGES: dict[frozenset[str], str] = {
    frozenset({"fire", "earth"}): "ваш мост — стабильный ритуал плюс живое действие. Ему нужна устойчивость, кому-то из вас нужна искра: планируйте спокойную основу и добавляйте движение.",
    frozenset({"fire", "air"}): "ваш мост — живость плюс разговор. Хорошо работают лёгкие планы, юмор, поездки, идеи и честный диалог без тяжёлого давления.",
    frozenset({"fire", "water"}): "ваш мост — энергия плюс бережность. Важно не гасить живость, но говорить мягко, чтобы чувства не превращались в пожарную тревогу.",
    frozenset({"earth", "air"}): "ваш мост — понятные договорённости плюс лёгкий диалог. Нужны и конкретика, и воздух, иначе один упрётся, а другой начнёт улетать в слова.",
    frozenset({"earth", "water"}): "ваш мост — уют плюс нежность. Это хороший союз для тепла, если не превращать заботу в молчаливые ожидания.",
    frozenset({"air", "water"}): "ваш мост — слова плюс чувство. Важно проговаривать эмоции мягко: не сухо анализировать, но и не ждать, что второй сам всё угадает.",
}

ELEMENT_NAMES: dict[str, str] = {
    "fire": "Огонь",
    "earth": "Земля",
    "air": "Воздух",
    "water": "Вода",
}


def _safe_name(name: str | None) -> str:
    cleaned = (name or "Партнёр").strip()
    return cleaned[:60] if cleaned else "Партнёр"


def _placement_line(label: str, placement: Placement | dict[str, object]) -> str:
    if isinstance(placement, dict):
        return f"{label}: {placement.get('sign_ru')}, стихия {placement.get('element_ru')}"
    return f"{label}: {placement.sign_ru}, стихия {placement.element_ru}"


def _placement(report: PartnerReport, key: str) -> dict[str, object]:
    return report.placements[key]


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
            f"Возможные варианты: {variants}. Ниже взята практическая середина дня. "
            "Для точности лучше знать время рождения. Да, данные опять решили поиграть в загадки."
        )

    text = f"""
🔑 Глубокий ключ к мужчине: {name}

Дата рождения: {chart.birth_date:%d.%m.%Y}

Главный вывод:
{name} легче раскрывается через язык: {moon.element_ru}.
{moon_meaning.core}{moon_note}

1. Эмоциональная база
{moon_meaning.title}

Что ему нужно:
{moon_meaning.needs}

Как это обычно проявляется:
{moon_meaning.how_it_shows}

Как поддержать:
{moon_meaning.how_to_support}

Что лучше не делать:
{moon_meaning.what_not_to_do}

2. Где ему приятно: Венера
{_placement_line("Венера", venus)}
{venus_text}

3. Как с ним говорить: Меркурий
{_placement_line("Меркурий", mercury)}
{mercury_text}

4. Как поддержать его силу: Марс
{_placement_line("Марс", mars)}
{mars_text}

5. Как сделать хорошо обоим
{moon_meaning.bridge}

Первый шаг:
{moon_meaning.first_step}

Важно:
Это не приговор отношениям и не проверка совместимости. Это мягкая карта понимания: какие условия помогают мужчине доверять, слышать и быть теплее.
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
    name = report.partner_name
    return f"""
💞 Как ему с тобой хорошо: {name}

Его эмоциональный язык: {report.emotional_language_title}

Главный смысл:
{meaning.core}

Что помогает ему оставаться рядом:
{meaning.needs}

Что может закрывать:
{meaning.what_not_to_do}

Первый шаг:
{meaning.first_step}

Дальше можно открыть точную Луну, добавить свою дату и увидеть мост между вами, или разобрать Венеру, Меркурий и Марс.
""".strip()


def format_moon_detail(report: PartnerReport) -> str:
    moon = _placement(report, "moon")
    meaning = MOON_MEANINGS[str(moon["element"])]
    sign = str(moon["sign_ru"])
    focus = MOON_SIGN_FOCUS.get(sign, meaning.needs)
    return f"""
🌙 Точная Луна мужчины: {report.partner_name}

{_placement_line("Луна", moon)}

Как именно ему эмоционально хорошо:
{focus}

Что ему нужно в близости:
{meaning.needs}

Что лучше не делать:
{meaning.what_not_to_do}

Практический ключ:
{meaning.first_step}
""".strip()


def format_venus_detail(report: PartnerReport) -> str:
    venus = _placement(report, "venus")
    return f"""
💗 Венера: где ему приятно

{_placement_line("Венера", venus)}

{VENUS_MEANINGS[str(venus["element"])]}

Как использовать:
создавай не спектакль ради впечатления, а такие условия, где ему приятно быть рядом: тон, атмосфера, внимание, ритм и маленькие жесты. Да, иногда любовь начинается не с судьбы, а с нормальной интонации.
""".strip()


def format_mercury_detail(report: PartnerReport) -> str:
    mercury = _placement(report, "mercury")
    return f"""
🗣 Меркурий: как с ним говорить

{_placement_line("Меркурий", mercury)}

{MERCURY_MEANINGS[str(mercury["element"])]}

Практический ключ:
начинай разговор не с претензии, а с ясной цели: «я хочу понять тебя и сделать нам спокойнее». Один разговор — один вопрос. Человеческий мозг и так перегрет, не надо открывать в нём 18 вкладок сразу.
""".strip()


def format_mars_detail(report: PartnerReport) -> str:
    mars = _placement(report, "mars")
    return f"""
🔥 Марс: как поддержать его силу

{_placement_line("Марс", mars)}

{MARS_MEANINGS[str(mars["element"])]}

Как поддержать:
не забирать у него инициативу и не толкать через давление. Лучше дать понятную цель, уважение к его способу действия и пространство проявиться.
""".strip()


def format_moon_bridge(partner: PartnerReport, user: PartnerReport) -> str:
    p_el = partner.emotional_language
    u_el = user.emotional_language
    p_name = partner.partner_name
    bridge = "у вас похожий эмоциональный язык. Это помогает быстрее понимать базовые потребности друг друга, но всё равно важно не считать, что второй обязан чувствовать ровно так же."
    if p_el != u_el:
        bridge = BRIDGES.get(frozenset({p_el, u_el}), "ваш мост — уважать разные способы восстановления и заранее договариваться, где каждому спокойно.")

    return f"""
💞 Как сделать хорошо обоим

{p_name}: {ELEMENT_NAMES.get(p_el, p_el)}
Ты: {ELEMENT_NAMES.get(u_el, u_el)}

Главный мост:
{bridge}

Что важно:
сначала создать эмоциональную базу, где мужчина не закрывается, а ты не теряешь себя. Хорошие отношения растут не из угадывания, а из понятного ритма, тепла и договорённостей. Ужасно практично, зато работает.
""".strip()


def format_message_templates(report: PartnerReport) -> str:
    lines = [f"✍️ Что можно написать: {report.partner_name}", ""]
    for index, template in enumerate(report.message_templates, start=1):
        lines.append(f"Вариант {index}:\n{template}")
        lines.append("")
    lines.append("Смысл не в том, чтобы манипулировать человеком. Смысл в том, чтобы говорить на языке, который ему легче услышать.")
    return "\n".join(lines).strip()
