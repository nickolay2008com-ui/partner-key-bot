from __future__ import annotations

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
from app.astro.report import PartnerReport, format_moon_precision_note, format_person_portrait
from app.astro.sign_bridge import (
    format_moon_pair_mechanic,
    format_moon_person_mechanic,
    format_moon_variant_pair,
)


ELEMENT_KEYWORDS = {
    "fire": "живость, отклик, движение, интерес",
    "earth": "спокойствие, тело, надёжность, понятность",
    "air": "разговор, лёгкость, ясность, пространство",
    "water": "мягкость, чувство, принятие, безопасность",
}

ELEMENT_NAMES = {"fire": "Огонь", "earth": "Земля", "air": "Воздух", "water": "Вода"}

SIGN_PREPOSITIONAL = {
    "Овен": "Овне",
    "Телец": "Тельце",
    "Близнецы": "Близнецах",
    "Рак": "Раке",
    "Лев": "Льве",
    "Дева": "Деве",
    "Весы": "Весах",
    "Скорпион": "Скорпионе",
    "Стрелец": "Стрельце",
    "Козерог": "Козероге",
    "Водолей": "Водолее",
    "Рыбы": "Рыбах",
}


MOON_INTRO = (
    "Луна — это не про красивые слова, а про внутренний режим безопасности: что помогает человеку "
    "выдохнуть, доверять и быть собой без защиты.\n\n"
    "В отношениях она показывает, в какой атмосфере человек раскрывается, а от чего начинает закрываться: "
    "темп, тон, телесный комфорт, свобода, забота, ясность или мягкий отклик.\n\n"
    "Если попасть в его Луну, контакт становится проще: меньше угадываний и проверок, больше понятных действий, "
    "тепла и устойчивости. Главный вопрос Луны: где ему спокойно рядом с вами?"
)

VENUS_INTRO = (
    "Венера в астрологической карте показывает принцип притяжения: что человек считает ценным, красивым, "
    "приятным и достойным выбора.\n\n"
    "Это точка вкуса, удовольствия, симпатии, обмена, денег, эстетики и способности принимать лучшее без внутреннего зажима.\n\n"
    "В отношениях Венера показывает, что человеку приятно, что он считает красивым и ценным, как чувствует симпатию, "
    "через что тянется ближе и какие проявления любви действительно попадают в него.\n\n"
    "В процветании Венера показывает, как приходит процветание: за счёт чего человек становится привлекательным, "
    "желанным, выбираемым и ценным для других. Где его вкус, стиль, мягкость, качество, эстетика или особая атмосфера "
    "превращаются в притяжение и обмен.\n\n"
    "Чтобы понять партнёра, Венера отвечает на вопрос: где у него включаются удовольствие, ценность и живое притяжение?"
)

MERCURY_INTRO = (
    "Меркурий в астрологической карте показывает стиль мышления и коммуникации: как человек слышит, "
    "объясняет, пишет, спорит, учится, задаёт вопросы, ведёт переговоры и оформляет смысл словами.\n\n"
    "В отношениях Меркурий показывает, через какой язык к человеку можно войти в понимание: где ему нужна логика, "
    "где мягкость, где прямота, где факты, где время подумать, а где живой диалог.\n\n"
    "В процветании Меркурий связан с переговорами, сделками, обучением, перепиской, объяснением ценности, "
    "продажей идей и способностью находить общий язык с людьми, рынком и обстоятельствами.\n\n"
    "Чтобы понять партнёра, Меркурий отвечает на вопрос: как он думает, слышит, объясняет и договаривается с миром?"
)

MARS_INTRO = (
    "Марс в астрологической карте показывает волю и способ действия: как человек хочет, движется, спорит, "
    "защищается, проявляет напор, сексуальность, инициативу, границы и способность брать своё.\n\n"
    "В отношениях Марс показывает, как человек делает шаг, как проявляет желание, как реагирует на сопротивление, "
    "где становится резким, как защищает своё направление и что включает в нём активное действие.\n\n"
    "В процветании Марс показывает способность достигать: идти к цели, конкурировать, выдерживать напряжение, "
    "принимать вызов, действовать в реальности и не оставлять желание только в фантазии.\n\n"
    "Чтобы понять партнёра, Марс отвечает на вопрос: как он движется к желаемому, как берёт своё и как действует под давлением?"
)

MOON_SHORT = (
    "Луна показывает, где человеку спокойно внутри и какая атмосфера помогает ему раскрыться без лишнего напряжения."
)
VENUS_SHORT = (
    "Венера показывает, где включаются краски жизни: ценность, вкус, притяжение, обмен и способность принимать лучшее."
)
MERCURY_SHORT = "Меркурий показывает, как человек мыслит, слышит, объясняет, ведёт переговоры и договаривается с миром."
MARS_SHORT = "Марс показывает, как человек движется, хочет, действует, защищается, берёт своё и достигает."


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


def _sign_ru_prepositional(report: PartnerReport, key: str) -> str:
    sign = _sign_ru(report, key)
    return SIGN_PREPOSITIONAL.get(sign, sign)


def _element_name(element: str) -> str:
    return ELEMENT_NAMES.get(element, "свой ритм")


def _basis(report: PartnerReport, key: str, label: str) -> str:
    return f"({label} в {_sign_ru_prepositional(report, key)}, {_element_ru(report, key)})"


def _your_word(label: str) -> str:
    return "ваша" if label in {"Луна", "Венера"} else "ваш"


def _couple_basis(man_report: PartnerReport, woman_report: PartnerReport, key: str, label: str) -> str:
    return f"(его {label} в {_sign_ru_prepositional(man_report, key)}, {_element_ru(man_report, key)}; {_your_word(label)} {label} в {_sign_ru_prepositional(woman_report, key)}, {_element_ru(woman_report, key)})"


def _element_text(report: PartnerReport, key: str) -> str:
    element = _element(report, key)
    if key == "venus":
        return VENUS_MEANINGS.get(
            element,
            "Тепло появляется через внимание, ценность, вкус и естественное притяжение.",
        )
    if key == "mercury":
        return MERCURY_MEANINGS.get(element, "Слова лучше слышатся, когда в них есть спокойствие и ясность.")
    if key == "mars":
        return MARS_MEANINGS.get(element, "В напряжении помогает вернуть ясность и уважение к темпу.")
    return MOON_MEANINGS[report.emotional_language].needs


def _sign_detail(report: PartnerReport, key: str) -> str:
    sign = _sign_key(report, key)
    if key == "moon":
        return MOON_SIGN_DETAILS.get(
            sign,
            "Точный знак Луны уточняет, какой формат эмоционального спокойствия человеку ближе.",
        )
    if key == "venus":
        return VENUS_SIGN_DETAILS.get(
            sign,
            "Точный знак Венеры уточняет, где у человека включаются ценность, вкус и притяжение.",
        )
    if key == "mercury":
        return MERCURY_SIGN_DETAILS.get(
            sign,
            "Точный знак Меркурия уточняет, как человеку легче мыслить, слышать слова и входить в договорённость.",
        )
    if key == "mars":
        return MARS_SIGN_DETAILS.get(
            sign,
            "Точный знак Марса уточняет, как человек движется, действует и защищает своё направление.",
        )
    return "Точный знак уточняет личный оттенок проявления."


def _current_moon_variant(report: PartnerReport) -> dict[str, object]:
    moon = _placement(report, "moon")
    return {
        "sign_key": moon.get("sign_key", ""),
        "sign_ru": moon.get("sign_ru", "не определён"),
        "element": moon.get("element", report.emotional_language),
        "element_ru": moon.get("element_ru", ""),
    }


def _moon_variants(report: PartnerReport) -> list[dict[str, object]]:
    variants = report.moon_variants if isinstance(report.moon_variants, list) else []
    if report.moon_status == "changed_during_day" and variants:
        result: list[dict[str, object]] = []
        seen: set[tuple[str, str]] = set()
        for item in variants:
            if not isinstance(item, dict):
                continue
            key = (str(item.get("sign_key", "")), str(item.get("element", "")))
            if key in seen:
                continue
            seen.add(key)
            result.append(item)
        return result or [_current_moon_variant(report)]
    return [_current_moon_variant(report)]


def _pair_precision_note(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    notes = [format_moon_precision_note(item) for item in (man_report, woman_report)]
    notes = [item for item in notes if item]
    return "\n\n".join(notes)


def _moon_pair_title(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    return (
        f"его Луна в {_sign_ru(man_report, 'moon')}, {_element_ru(man_report, 'moon')} + "
        f"ваша Луна в {_sign_ru(woman_report, 'moon')}, {_element_ru(woman_report, 'moon')}"
    )


def _element_background(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    man_element = _element_name(man_report.emotional_language)
    woman_element = _element_name(woman_report.emotional_language)
    man_keywords = ELEMENT_KEYWORDS.get(man_report.emotional_language, "свой ритм")
    woman_keywords = ELEMENT_KEYWORDS.get(woman_report.emotional_language, "свой ритм")
    return (
        f"Фон стихий: {man_element} + {woman_element}.\n"
        f"У него общий эмоциональный климат: {man_keywords}.\n"
        f"У вас общий эмоциональный климат: {woman_keywords}.\n"
        "Стихия показывает климат, но точный механизм даёт знак Луны — поэтому ниже разбор идёт именно через знаки."
    )


def _alternate_moon_bridge_block(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    if man_report.moon_status != "changed_during_day" and woman_report.moon_status != "changed_during_day":
        return ""
    lines = [
        "Возможные варианты описания без точного времени рождения:",
        "Ниже не один окончательный вывод, а развилка по Луне. Выберите вариант, который больше похож на реальное поведение и эмоциональный ритм.",
    ]
    seen: set[tuple[str, str, str, str]] = set()
    for man_variant in _moon_variants(man_report):
        for woman_variant in _moon_variants(woman_report):
            key = (
                str(man_variant.get("sign_key", "")),
                str(man_variant.get("element", "")),
                str(woman_variant.get("sign_key", "")),
                str(woman_variant.get("element", "")),
            )
            if key in seen:
                continue
            seen.add(key)
            lines.append("\nЕсли " + format_moon_variant_pair(man_variant, woman_variant))
    return "\n\n".join(lines).strip()


def _profile_integral(report: PartnerReport) -> str:
    moon = f"Луна в {_sign_ru(report, 'moon')} — {_element_ru(report, 'moon')}"
    venus = f"Венера в {_sign_ru(report, 'venus')} — {_element_ru(report, 'venus')}"
    mercury = f"Меркурий в {_sign_ru(report, 'mercury')} — {_element_ru(report, 'mercury')}"
    mars = f"Марс в {_sign_ru(report, 'mars')} — {_element_ru(report, 'mars')}"
    return (
        f"Связка карты: {moon}; {venus}; {mercury}; {mars}. "
        "Человека лучше понимать не по одному признаку, а по сочетанию: где ему спокойно, "
        "где включаются краски жизни, как он мыслит и как движется к желаемому."
    )


def _person_deep_profile(report: PartnerReport, title: str) -> str:
    moon_meaning = MOON_MEANINGS[report.emotional_language]
    moon_item = _placement(report, "moon")
    return f"""
{title}: подробнее

🌙 Луна — где человеку спокойно {_basis(report, "moon", "Луна")}:
{MOON_SHORT}

Точный механизм Луны в {_sign_ru(report, "moon")}:
{format_moon_person_mechanic(moon_item, role="Его")}

Как это может проявляться:
{moon_meaning.how_it_shows}

💗 Венера — где включаются краски жизни {_basis(report, "venus", "Венера")}:
{VENUS_SHORT}

Стихийная база: {_element_text(report, "venus")}

Точный оттенок Венеры в {_sign_ru(report, "venus")}:
{_sign_detail(report, "venus")}

🗣 Меркурий — как человек мыслит и договаривается {_basis(report, "mercury", "Меркурий")}:
{MERCURY_SHORT}

Стихийная база: {_element_text(report, "mercury")}

Точный оттенок Меркурия в {_sign_ru(report, "mercury")}:
{_sign_detail(report, "mercury")}

🔥 Марс — как человек движется и достигает {_basis(report, "mars", "Марс")}:
{MARS_SHORT}

Стихийная база: {_element_text(report, "mars")}

Точный оттенок Марса в {_sign_ru(report, "mars")}:
{_sign_detail(report, "mars")}

Итог:
{_profile_integral(report)}
""".strip()


def format_moon_detail(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    precision_note = format_moon_precision_note(report)
    precision_block = f"\n\n{precision_note}" if precision_note else ""
    moon_basis = _basis(report, "moon", "Луна")
    alternate = ""
    if report.moon_status == "changed_during_day":
        variant_lines = []
        for variant in _moon_variants(report):
            variant_lines.append(format_moon_person_mechanic(variant, role="Если"))
        alternate = "\n\nВозможные варианты Луны без точного времени рождения:\n" + "\n\n".join(variant_lines)
    return f"""
🌙 Луна — где ему спокойно: {report.partner_name}

{MOON_INTRO}

Его Луна: {_sign_ru(report, "moon")}, стихия {_element_ru(report, "moon")}{precision_block}

Что это значит простыми словами:
{format_moon_person_mechanic(_placement(report, "moon"), role="Его")}{alternate}

Что может сбивать контакт {moon_basis}:
{meaning.what_not_to_do}

Мягкий ключ {moon_basis}:
{meaning.first_step}
""".strip()


def format_venus_detail(report: PartnerReport) -> str:
    venus_basis = _basis(report, "venus", "Венера")
    return f"""
💗 Венера — где включаются краски жизни: {report.partner_name}

{VENUS_INTRO}

Венера: {_sign_ru(report, "venus")}, стихия {_element_ru(report, "venus")}

Стихийная база:
{_element_text(report, "venus")}

Точный оттенок Венеры в {_sign_ru(report, "venus")}:
{_sign_detail(report, "venus")}

Что особенно работает {venus_basis}:
искренний формат ценности, вкуса и притяжения, который совпадает не только со стихией, но и с конкретным знаком Венеры.

Мягкий ключ:
не стараться любой ценой понравиться, а увидеть, где у человека включаются краски жизни, ценность и естественное притяжение.
""".strip()


def format_mercury_detail(report: PartnerReport) -> str:
    mercury_basis = _basis(report, "mercury", "Меркурий")
    return f"""
🗣 Меркурий — как человек мыслит и договаривается: {report.partner_name}

{MERCURY_INTRO}

Меркурий: {_sign_ru(report, "mercury")}, стихия {_element_ru(report, "mercury")}

Стихийная база:
{_element_text(report, "mercury")}

Точный оттенок Меркурия в {_sign_ru(report, "mercury")}:
{_sign_detail(report, "mercury")}

Что особенно важно {mercury_basis}:
не только подобрать правильные слова, но и попасть в способ мышления: темп, тон, прямоту, мягкость, факты или структуру.

Мягкий ключ:
начинать не с давления, а с намерения: «Я хочу понять, как ты это видишь».
""".strip()


def format_mars_detail(report: PartnerReport) -> str:
    mars_basis = _basis(report, "mars", "Марс")
    return f"""
🔥 Марс — как человек движется и достигает: {report.partner_name}

{MARS_INTRO}

Марс: {_sign_ru(report, "mars")}, стихия {_element_ru(report, "mars")}

Стихийная база:
{_element_text(report, "mars")}

Точный оттенок Марса в {_sign_ru(report, "mars")}:
{_sign_detail(report, "mars")}

Что особенно важно {mars_basis}:
в напряжении человек часто показывает не только характер, но и способ двигаться к желаемому, защищать своё направление и действовать под давлением.

Мягкий ключ:
не тянуть силой в свой темп, а понять, как человек движется, достигает и где ему нужен понятный следующий шаг.
""".strip()


def format_couple_moon_bridge(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    precision_note = _pair_precision_note(man_report, woman_report)
    precision_block = f"\n\n{precision_note}" if precision_note else ""
    mechanic = format_moon_pair_mechanic(_placement(man_report, "moon"), _placement(woman_report, "moon"))
    alternate_block = _alternate_moon_bridge_block(man_report, woman_report)
    alternate_text = f"\n\n{alternate_block}" if alternate_block else ""
    return f"""
💞 Ваш эмоциональный мост

{_moon_pair_title(man_report, woman_report)}{precision_block}

{mechanic}

{_element_background(man_report, woman_report)}{alternate_text}

Гармония здесь не в том, чтобы кто-то стал удобнее. Она в том, чтобы увидеть конкретный механизм Луны каждого и найти между ними живой, тёплый проход.
""".strip()


def format_couple_portraits(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    return f"""
👤 Портреты в отношениях

{format_person_portrait(man_report, "👤 Его портрет в отношениях")}

{format_person_portrait(woman_report, "👤 Ваш портрет в отношениях")}

Общий вектор:
эти два портрета нужны не для ярлыков, а чтобы увидеть, чем наполняется каждый. Когда пара уважает оба ритма, отношения получают больше тепла, ясности, желания действовать вместе и пространства для процветания.
""".strip()


def format_couple_full_report(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    precision_note = _pair_precision_note(man_report, woman_report)
    precision_block = f"\n\nТочность Луны:\n{precision_note}" if precision_note else ""
    moon_basis = _couple_basis(man_report, woman_report, "moon", "Луна")
    venus_basis = _couple_basis(man_report, woman_report, "venus", "Венера")
    mercury_basis = _couple_basis(man_report, woman_report, "mercury", "Меркурий")
    mars_basis = _couple_basis(man_report, woman_report, "mars", "Марс")
    mechanic = format_moon_pair_mechanic(_placement(man_report, "moon"), _placement(woman_report, "moon"))
    alternate_block = _alternate_moon_bridge_block(man_report, woman_report)
    alternate_text = f"\n\n{alternate_block}" if alternate_block else ""
    return f"""
📖 Карта гармонии пары: {man_report.partner_name} + {woman_report.partner_name}

Эта карта не говорит, подходите вы друг другу или нет. Она показывает, какой эмоциональный ритм возникает между вами и где в нём можно найти больше тепла, ясности и доверия.

Ваш главный ритм {moon_basis}:{precision_block}

{mechanic}

{_element_background(man_report, woman_report)}{alternate_text}

👤 Он подробнее
{_person_deep_profile(man_report, man_report.partner_name)}

👤 Она / вы подробнее
{_person_deep_profile(woman_report, woman_report.partner_name)}

💗 Венера — где включаются краски жизни {venus_basis}
{VENUS_SHORT}

Его Венера: {_sign_ru(man_report, "venus")}, стихия {_element_ru(man_report, "venus")}
Стихийная база: {_element_text(man_report, "venus")}
Точный оттенок его Венеры в {_sign_ru(man_report, "venus")}:
{_sign_detail(man_report, "venus")}

Ваша Венера: {_sign_ru(woman_report, "venus")}, стихия {_element_ru(woman_report, "venus")}
Стихийная база: {_element_text(woman_report, "venus")}
Точный оттенок вашей Венеры в {_sign_ru(woman_report, "venus")}:
{_sign_detail(woman_report, "venus")}

Здесь важно не копировать чужой способ любить, а почувствовать, где у каждого включаются краски жизни, ценность и притяжение.

🗣 Меркурий — как человек мыслит и договаривается {mercury_basis}
{MERCURY_SHORT}

Его Меркурий: {_sign_ru(man_report, "mercury")}, стихия {_element_ru(man_report, "mercury")}
Стихийная база: {_element_text(man_report, "mercury")}
Точный оттенок его Меркурия в {_sign_ru(man_report, "mercury")}:
{_sign_detail(man_report, "mercury")}

Ваш Меркурий: {_sign_ru(woman_report, "mercury")}, стихия {_element_ru(woman_report, "mercury")}
Стихийная база: {_element_text(woman_report, "mercury")}
Точный оттенок вашего Меркурия в {_sign_ru(woman_report, "mercury")}:
{_sign_detail(woman_report, "mercury")}

Слова становятся мостом, когда они учитывают не только тему разговора, но и способ мышления человека.

🔥 Марс — как человек движется и достигает {mars_basis}
{MARS_SHORT}

Его Марс: {_sign_ru(man_report, "mars")}, стихия {_element_ru(man_report, "mars")}
Стихийная база: {_element_text(man_report, "mars")}
Точный оттенок его Марса в {_sign_ru(man_report, "mars")}:
{_sign_detail(man_report, "mars")}

Ваш Марс: {_sign_ru(woman_report, "mars")}, стихия {_element_ru(woman_report, "mars")}
Стихийная база: {_element_text(woman_report, "mars")}
Точный оттенок вашего Марса в {_sign_ru(woman_report, "mars")}:
{_sign_detail(woman_report, "mars")}

Напряжение не обязательно разрушает пару. Иногда оно просто показывает, что два ритма движения пока не нашли общий шаг.

Мягкий вывод:
Гармония здесь не в том, чтобы стать одинаковыми. Она в том, чтобы распознать ритм друг друга и перестать воевать с тем, что на самом деле просит понимания.
""".strip()


def format_full_report_intro(report: PartnerReport) -> str:
    return f"""
📖 Карта гармонии пары

Чтобы собрать карту пары, нужна не только дата мужчины, но и ваша дата рождения.

Сейчас открыт разбор {report.partner_name}. Добавьте свою дату, чтобы увидеть общий эмоциональный ритм: где ему спокойнее, где живее вам, и какой мост может появиться между вами.
""".strip()
