from __future__ import annotations

from app.astro.meanings import MARS_MEANINGS, MERCURY_MEANINGS, MOON_MEANINGS, MOON_SIGN_DETAILS, VENUS_MEANINGS
from app.astro.report import PartnerReport


def _placement(report: PartnerReport, key: str) -> dict[str, object]:
    value = report.placements.get(key)
    return value if isinstance(value, dict) else {}


def _sign_ru(report: PartnerReport, key: str) -> str:
    return str(_placement(report, key).get("sign_ru", "не определён"))


def _sign_key(report: PartnerReport, key: str) -> str:
    return str(_placement(report, key).get("sign_key", ""))


def _element(report: PartnerReport, key: str) -> str:
    return str(_placement(report, key).get("element", report.emotional_language))


def _element_ru(report: PartnerReport, key: str) -> str:
    return str(_placement(report, key).get("element_ru", ""))


def format_moon_detail(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    sign_text = MOON_SIGN_DETAILS.get(
        _sign_key(report, "moon"),
        "Точный знак уточняет, какой именно формат спокойствия человеку ближе.",
    )
    return f"""
🌙 Точная Луна мужчины: {report.partner_name}

Луна: {_sign_ru(report, "moon")}, стихия {_element_ru(report, "moon")}

Луна показывает базовое эмоциональное состояние: где ему спокойно, где он меньше закрывается и куда ему легче возвращаться.

Как именно ему хорошо:
{sign_text}

Практический ключ:
{meaning.how_to_support}

Чего лучше избегать:
{meaning.what_not_to_do}

Мягкий первый шаг:
{meaning.first_step}
""".strip()


def format_venus_detail(report: PartnerReport) -> str:
    element = _element(report, "venus")
    return f"""
💗 Венера мужчины: где ему приятно

Венера: {_sign_ru(report, "venus")}, стихия {_element_ru(report, "venus")}

Венера показывает, через что человеку приятнее получать симпатию, внимание и тепло.

Как это проявляется:
{VENUS_MEANINGS.get(element, "Ему важны приятность, внимание и мягкий контакт.")}

Как применить:
Сделай маленький жест в его стиле: понятный сигнал внимания, который ему легче принять.
""".strip()


def format_mercury_detail(report: PartnerReport) -> str:
    element = _element(report, "mercury")
    return f"""
🗣 Меркурий мужчины: как с ним говорить

Меркурий: {_sign_ru(report, "mercury")}, стихия {_element_ru(report, "mercury")}

Меркурий показывает, как человеку легче воспринимать слова, объяснения и сложные разговоры.

Как говорить:
{MERCURY_MEANINGS.get(element, "Лучше говорить спокойно, ясно и без нажима.")}

Практический ключ:
Начинай не с претензии, а с цели разговора: «Я хочу понять нас, а не спорить». Потом один конкретный вопрос.
""".strip()


def format_mars_detail(report: PartnerReport) -> str:
    element = _element(report, "mars")
    return f"""
🔥 Марс мужчины: как поддержать его силу

Марс: {_sign_ru(report, "mars")}, стихия {_element_ru(report, "mars")}

Марс показывает, как человек действует, проявляет инициативу и идёт к цели.

В напряжении:
{MARS_MEANINGS.get(element, "В напряжении лучше вернуть спокойствие и ясность.")}

Как поддержать:
Дай ясность, уважение к его темпу и конкретный следующий шаг. Так человеку легче проявляться без внутреннего сопротивления.
""".strip()


def format_couple_moon_bridge(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    man_meaning = MOON_MEANINGS[man_report.emotional_language]
    woman_meaning = MOON_MEANINGS[woman_report.emotional_language]
    if man_report.emotional_language == woman_report.emotional_language:
        bridge = "Ваши эмоциональные языки похожи. Это помогает быстрее понимать базовые реакции друг друга. Важно не усиливать одну и ту же крайность."
    else:
        bridge = "Ваши эмоциональные языки разные. Это точка настройки: ему важно дать его форму спокойствия, а тебе — не потерять свою."
    return f"""
💞 Как сделать хорошо обоим

Его Луна:
{man_report.emotional_language_title}

Твоя Луна:
{woman_report.emotional_language_title}

Что ему нужно:
{man_meaning.needs}

Что нужно тебе:
{woman_meaning.needs}

Ваш мост:
{bridge}

Практика на ближайшие дни:
Сделайте один маленький ритуал, где есть его спокойствие и твоя потребность: понятный план, тёплый разговор, спокойная встреча или немного живости в устойчивом формате.
""".strip()


def format_full_report_intro(report: PartnerReport) -> str:
    return f"""
📖 Карта гармонии пары

Сейчас открыт базовый разбор мужчины: Луна, Венера, Меркурий и Марс.

Следующий сильный слой — добавить твою дату рождения и собрать мост пары: где ему хорошо, где тебе хорошо, как говорить и какой ритм поможет отношениям развиваться.

Начни с кнопки «💞 Сравнить ваши Луны». Это самый чистый шаг перед большим HTML-отчётом.

Ниже — текущий глубокий разбор {report.partner_name}.

{report.text}
""".strip()
