from __future__ import annotations

from app.astro.meanings import MARS_MEANINGS, MERCURY_MEANINGS, MOON_MEANINGS, MOON_SIGN_DETAILS, VENUS_MEANINGS
from app.astro.report import PartnerReport


ELEMENT_CORE = {
    "fire": "живость, движение, быстрый отклик и вдохновение",
    "earth": "стабильность, телесный комфорт, понятность и надёжность",
    "air": "разговор, лёгкость, ясность и пространство",
    "water": "мягкость, чувство, принятие и эмоциональную безопасность",
}


BRIDGE_MAP = {
    ("fire", "fire"): ("общий огонь", "Вам обоим нужен живой отклик, движение и ощущение, что отношения не застывают.", "Риск — быстро вспыхивать и так же быстро спорить. Держите темп, но заранее договаривайтесь, как останавливать конфликт."),
    ("fire", "earth"): ("движение + устойчивость", "Одному важна живость и импульс, другому — стабильность и понятность.", "Мост: сначала понятная основа, потом живой элемент: прогулка, поездка, новый вкус, совместное действие."),
    ("fire", "air"): ("движение + разговор", "Огонь даёт инициативу, Воздух помогает проговорить желания без давления.", "Мост: сначала лёгкий разговор, потом конкретное действие. Не превращать всё в бесконечное обсуждение."),
    ("fire", "water"): ("тепло + бережный темп", "Огню важен быстрый отклик, Воде — эмоциональная безопасность.", "Мост: проявлять инициативу мягко, без резкости и проверки чувств."),
    ("earth", "fire"): ("устойчивость + живость", "Одному важно спокойствие, другому — движение и ощущение развития.", "Мост: понятный план плюс маленький живой элемент. Так отношения не превращаются ни в хаос, ни в болото."),
    ("earth", "earth"): ("общая устойчивость", "Вам обоим важны надёжность, простые действия и понятный ритм.", "Риск — застрять в привычном. Добавляйте маленькие обновления, не ломая стабильность."),
    ("earth", "air"): ("конкретика + разговор", "Земле нужна практичность, Воздуху — слова и пространство.", "Мост: сначала обсудить, потом закрепить одним понятным действием."),
    ("earth", "water"): ("надёжность + мягкость", "Земля даёт опору, Вода — эмоциональное тепло.", "Мост: забота делом плюс бережные слова. Не молчать там, где другому нужна мягкая включённость."),
    ("air", "fire"): ("разговор + действие", "Воздуху важно понять и обсудить, Огню — почувствовать живость и движение.", "Мост: короткий ясный разговор и сразу маленький шаг в реальности."),
    ("air", "earth"): ("ясность + устойчивость", "Воздуху нужны слова и свобода, Земле — понятность и надёжность.", "Мост: проговаривать ожидания и переводить их в конкретный план."),
    ("air", "air"): ("общий диалог", "Вам обоим легче через разговор, объяснение, юмор и пространство.", "Риск — много обсуждать и мало делать. После разговора выбирайте один следующий шаг."),
    ("air", "water"): ("слова + чувство", "Воздуху важна ясность, Воде — тон, безопасность и эмоциональное участие.", "Мост: говорить прямо, но мягко. Не прятать чувства за холодной логикой."),
    ("water", "fire"): ("бережность + живость", "Воде нужна мягкость, Огню — движение и инициативность.", "Мост: сначала создать эмоциональную безопасность, потом добавлять живое действие."),
    ("water", "earth"): ("чувство + опора", "Воде важно тепло, Земле — стабильность и конкретика.", "Мост: мягкие слова подтверждать простыми действиями."),
    ("water", "air"): ("чувство + ясность", "Воде нужна эмоциональная бережность, Воздуху — разговор и пространство.", "Мост: объяснять чувства словами, но не превращать разговор в допрос."),
    ("water", "water"): ("общее чувство", "Вам обоим важны мягкость, доверие и эмоциональная включённость.", "Риск — утонуть в настроениях. Нужны простые договорённости и бережные границы."),
}


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


def _bridge_for(left: str, right: str) -> tuple[str, str, str]:
    return BRIDGE_MAP.get((left, right), ("общий ритм", "Ваши эмоциональные языки можно соединить через уважение к разным потребностям.", "Мост: не требовать одинаковых реакций, а договариваться о понятном общем шаге."))


def format_moon_detail(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    sign_text = MOON_SIGN_DETAILS.get(_sign_key(report, "moon"), "Точный знак уточняет, какой именно формат спокойствия человеку ближе.")
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
    title, dynamic, bridge = _bridge_for(man_report.emotional_language, woman_report.emotional_language)
    return f"""
💞 Ваш эмоциональный мост

Ему спокойнее через:
{man_report.emotional_language_title}

Вам спокойнее через:
{woman_report.emotional_language_title}

Главный ритм пары:
{title}

Что важно ему:
{man_meaning.needs}

Что важно вам:
{woman_meaning.needs}

Где может быть напряжение:
{dynamic}

Как соединить:
{bridge}

Практика на ближайшие дни:
Выберите один маленький общий ритуал, где есть его потребность и ваша потребность. Не «кто прав», а «какой формат помогает нам обоим быть спокойнее и ближе».

Фраза для мягкого начала:
«Мне хочется лучше понять наш общий ритм: где тебе спокойно, где мне хорошо, и как нам сделать контакт теплее без давления».
""".strip()


def format_couple_full_report(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    title, dynamic, bridge = _bridge_for(man_report.emotional_language, woman_report.emotional_language)
    man_moon = MOON_MEANINGS[man_report.emotional_language]
    woman_moon = MOON_MEANINGS[woman_report.emotional_language]
    man_venus = VENUS_MEANINGS.get(_element(man_report, "venus"), "Ему важны внимание, приятность и тёплый контакт.")
    woman_venus = VENUS_MEANINGS.get(_element(woman_report, "venus"), "Вам важны внимание, приятность и тёплый контакт.")
    man_mercury = MERCURY_MEANINGS.get(_element(man_report, "mercury"), "Лучше говорить спокойно и ясно.")
    woman_mercury = MERCURY_MEANINGS.get(_element(woman_report, "mercury"), "Вам легче через спокойный и ясный разговор.")
    man_mars = MARS_MEANINGS.get(_element(man_report, "mars"), "В напряжении лучше вернуть спокойствие и ясность.")
    woman_mars = MARS_MEANINGS.get(_element(woman_report, "mars"), "В напряжении вам помогает ясность и уважение к темпу.")
    return f"""
📖 Карта гармонии пары: {man_report.partner_name} + {woman_report.partner_name}

Эта карта не решает за вас, подходите вы друг другу или нет. Она показывает, как лучше понимать друг друга: где каждому спокойно, как проявлять тепло, как говорить без давления и какой ритм помогает отношениям развиваться.

Главный вывод:
{man_report.partner_name} легче раскрывается через {ELEMENT_CORE.get(man_report.emotional_language, "свой эмоциональный ритм")}.
{woman_report.partner_name} легче раскрывается через {ELEMENT_CORE.get(woman_report.emotional_language, "свой эмоциональный ритм")}.

Ваш главный мост:
{title}. {bridge}

1. Эмоциональная база
Ему важно:
{man_moon.needs}

Вам важно:
{woman_moon.needs}

Где может быть напряжение:
{dynamic}

2. Как проявлять тепло
Его Венера: {_sign_ru(man_report, "venus")}, стихия {_element_ru(man_report, "venus")}
{man_venus}

Ваша Венера: {_sign_ru(woman_report, "venus")}, стихия {_element_ru(woman_report, "venus")}
{woman_venus}

Мост по теплу:
Делайте маленькие жесты, которые учитывают оба способа получать приятность: не только то, что удобно одному, а то, что создаёт взаимность.

3. Как говорить
Его Меркурий: {_sign_ru(man_report, "mercury")}, стихия {_element_ru(man_report, "mercury")}
{man_mercury}

Ваш Меркурий: {_sign_ru(woman_report, "mercury")}, стихия {_element_ru(woman_report, "mercury")}
{woman_mercury}

Формула разговора:
«Я хочу понять нас, а не спорить» → один конкретный вопрос → пауза → один общий следующий шаг.

4. Действие и напряжение
Его Марс: {_sign_ru(man_report, "mars")}, стихия {_element_ru(man_report, "mars")}
{man_mars}

Ваш Марс: {_sign_ru(woman_report, "mars")}, стихия {_element_ru(woman_report, "mars")}
{woman_mars}

Мост по действиям:
Не тянуть друг друга силой в свой темп. Сначала назвать цель, потом выбрать маленький реальный шаг.

5. Практика на 7 дней
1) Один спокойный разговор без претензий.
2) Один маленький жест в его эмоциональном языке.
3) Один маленький жест в вашем эмоциональном языке.
4) Один общий план без давления.
5) Один приятный совместный ритуал.
6) Одна честная фраза вместо проверки или молчания.
7) Один вопрос: «Что стало между нами теплее?»

Что лучше не делать:
Не требовать одинаковых реакций, не проверять чувства холодом, не превращать карту в приговор и не подстраиваться до потери себя. Задача карты — найти общий ритм, а не назначить виноватого.
""".strip()


def format_full_report_intro(report: PartnerReport) -> str:
    return f"""
📖 Карта гармонии пары

Чтобы собрать карту пары, нужна не только дата мужчины, но и ваша дата рождения.

Сейчас открыт разбор {report.partner_name}. Добавьте свою дату, чтобы увидеть общий мост: где спокойно ему, где хорошо вам, как говорить и какой ритм помогает отношениям развиваться.
""".strip()
