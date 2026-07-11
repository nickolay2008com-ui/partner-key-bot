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


MODERN_ASTROLOGER_CONTEXT = (
    "Подход современного практикующего астролога: не делать фатальный вывод по одному знаку и не клеить "
    "на мужчину заводскую наклейку. Мы читаем связку планеты, знака и реального поведения: Луна показывает "
    "эмоциональную безопасность, Венера — ценность и притяжение, Меркурий — язык понимания, Марс — действие "
    "и напряжение. Поэтому каждый блок ниже переведён в наблюдаемые сигналы: что человеку нужно, где он "
    "закрывается и какой маленький шаг улучшает контакт без режима «угадай пароль от сердца»."
)

PLANET_EXPERT_LENS = {
    "moon": (
        "Астрологический фокус: Луну читают как базовую нервную систему отношений — не образ любви, "
        "а то, что возвращает человеку чувство дома, безопасности и внутреннего разрешения быть собой."
    ),
    "venus": (
        "Астрологический фокус: Венеру читают как стиль выбора, удовольствия и ценности — не только романтику, "
        "но и то, через что человек чувствует вкус жизни, красоту обмена и желание приближаться."
    ),
    "mercury": (
        "Астрологический фокус: Меркурий читают как способ обработки информации — темп мысли, форму диалога, "
        "переписку, переговоры и то, какие слова становятся мостом, а какие звучат как напор."
    ),
    "mars": (
        "Астрологический фокус: Марс читают как волю и реакцию на сопротивление — как человек хочет, спорит, "
        "защищает границы, берёт инициативу и превращает напряжение в действие."
    ),
    "jupiter": (
        "Астрологический фокус: Юпитер читают как вектор расширения — где человек видит смысл, "
        "легче доверяет будущему, растёт, делится ресурсом и строит большой горизонт."
    ),
}

PLANET_PRACTICE_PROMPTS = {
    "moon": (
        "Как проверить в жизни: посмотрите, после какого формата общения человек заметно расслабляется — "
        "после тепла, ясного плана, разговора, свободы или совместного действия. Это важнее красивой формулы."
    ),
    "venus": (
        "Как проверить в жизни: отметьте, на какие проявления человек откликается сам — комплименты, заботу делом, "
        "эстетику, игру, интеллектуальный интерес, глубину или атмосферу. Венера видна там, где появляется добровольное притяжение."
    ),
    "mercury": (
        "Как проверить в жизни: меняйте не смысл, а форму подачи — короче или мягче, конкретнее или легче, "
        "письменно или голосом — и смотрите, где человек начинает слышать без обороны."
    ),
    "mars": (
        "Как проверить в жизни: наблюдайте момент напряжения — человек ускоряется, упирается, спорит, закрывается "
        "или берёт структуру. Марс лучше всего виден не в словах о желаниях, а в способе действовать в напряжении."
    ),
    "jupiter": (
        "Как проверить в жизни: смотрите, от каких тем человек оживает и начинает думать шире — обучение, "
        "дом, дело, путешествия, статус, свобода, творчество или помощь другим."
    ),
}

PLANET_ACTION_KEYS = {
    "moon": {
        "default": (
            "Польза для отношений: дать человеку именно тот формат спокойствия, в котором он не уходит в защиту.\n"
            "Что усиливает: тёплый тон, уважение к его ритму и одна понятная просьба вместо эмоционального техзадания на 40 пунктов.\n"
            "Что снижает близость: проверки, резкие исчезновения, холодная ирония и попытка заставить чувствовать «правильно».\n"
            "Мини-шаг: спросить, что сейчас даст ему больше спокойствия — разговор, пауза, объятие, план или совместное действие."
        ),
    },
    "venus": {
        "default": (
            "Польза для отношений: попадать не в абстрактную романтику, а в его личный язык ценности.\n"
            "Что усиливает: персональный жест — комплимент, забота делом, эстетика, игра, глубина или атмосфера именно в его стиле.\n"
            "Что снижает притяжение: универсальные сценарии из интернета, давление на признания и подарки «лишь бы было».\n"
            "Мини-шаг: выбрать один жест, который покажет «я вижу, что для тебя ценно», и посмотреть на живой отклик."
        ),
    },
    "mercury": {
        "default": (
            "Польза для отношений: менять не любовь, а формат передачи сигнала — иногда проблема не в чувстве, а в упаковке фразы.\n"
            "Что усиливает: один ясный смысл, спокойный тон, вопрос вместо допроса и договорённость, что делаем дальше.\n"
            "Что снижает понимание: намёки с субтитрами, длинные обвинительные лекции и ожидание, что он сам скачает обновление телепатии.\n"
            "Мини-шаг: сформулировать мысль в одну фразу: «мне важно…, я прошу…, как тебе такой вариант?»"
        ),
    },
    "jupiter": {
        "default": (
            "Польза для отношений: поддерживать его рост без роли внутреннего начальника отдела мотивации.\n"
            "Что усиливает: интерес к его горизонту, вера в маленький следующий шаг и уважение к личному смыслу.\n"
            "Что снижает масштаб: сравнение с чужими успехами, давление «ты должен больше» и обещания без опоры.\n"
            "Мини-шаг: спросить, какой горизонт ему сейчас правда интересен, и договориться об одном реальном шаге на неделю."
        ),
    },
    "mars": {
        "libra": (
            "Польза для отношений: не требовать мгновенного рывка, а предложить выбор из 2–3 честных вариантов "
            "и сразу зафиксировать следующий шаг.\n"
            "Что усиливает: спокойная формулировка «давай найдём решение, где никто не проигрывает».\n"
            "Что снижает силу: напор, ультиматумы, сравнение и спор без финального решения.\n"
            "Мини-шаг: договориться, кто что делает и к какому сроку возвращает ответ."
        ),
        "default": (
            "Польза для отношений: переводить напряжение в понятный следующий шаг, а не оставлять его в догадках.\n"
            "Что усиливает: уважение к его способу действовать, ясная цель и короткая договорённость.\n"
            "Что снижает силу: напор, обесценивание темпа и конфликт ради самого конфликта.\n"
            "Мини-шаг: назвать желание, границу и одно действие, которое можно сделать уже сейчас."
        ),
    },
}


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
    "Луна — это раздел инструкции «как не включить защитный режим». Она показывает не красивые обещания, "
    "а внутренний режим безопасности: что помогает мужчине выдохнуть, доверять и быть собой без брони.\n\n"
    "В отношениях Луна отвечает за атмосферу: темп, тон, телесный комфорт, свободу, заботу, ясность или мягкий "
    "отклик. Если попасть в этот режим, не нужно нажимать на все кнопки сразу — человек сам становится теплее, "
    "спокойнее и понятнее.\n\n"
    "Практический вопрос Луны: где ему рядом с вами спокойно настолько, что он перестаёт обороняться?"
)

VENUS_INTRO = (
    "Венера — это раздел «что для него красиво, ценно и почему он тянется ближе». Не гарантийный талон на романтику, "
    "а карта вкуса: какие жесты попадают в сердце, а какие выглядят как рассылка без персонализации.\n\n"
    "В отношениях Венера показывает, что человеку приятно, как он выбирает, на какие проявления симпатии откликается "
    "и где чувствует: «да, вот это моё». В процветании она показывает, через что он становится привлекательным, "
    "желанным и ценным для других — стиль, качество, атмосфера, связи, забота или яркость.\n\n"
    "Практический вопрос Венеры: каким способом дать ему чувство ценности так, чтобы это было не громко, а точно?"
)

MERCURY_INTRO = (
    "Меркурий — это раздел инструкции «как говорить, чтобы вас услышали, а не просто получили уведомление». "
    "Он показывает стиль мышления: как мужчина слышит, объясняет, пишет, спорит, учится и оформляет смысл словами.\n\n"
    "В отношениях Меркурий подсказывает язык доступа: где нужна логика, где мягкость, где прямота, где факты, "
    "где пауза подумать, а где живой диалог. В процветании он связан с переговорами, обучением, сделками, "
    "перепиской и способностью объяснить ценность без лишнего шума.\n\n"
    "Практический вопрос Меркурия: в какой форме одна и та же мысль перестаёт звучать как претензия и становится мостом?"
)

MARS_INTRO = (
    "Марс — это раздел «двигатель, тормоза и что делать, если загорелась лампочка напряжения». Он показывает волю: "
    "как мужчина хочет, действует, спорит, защищает границы, проявляет инициативу и берёт своё.\n\n"
    "В отношениях Марс показывает, как он делает шаг, реагирует на сопротивление, где становится резким и что возвращает "
    "ему здоровое действие. В процветании Марс отвечает за достижение: цель, конкуренцию, выдержку и способность не оставлять "
    "желание только в фантазии.\n\n"
    "Практический вопрос Марса: как перевести напряжение не в ссору, а в ясный следующий шаг?"
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


def _is_retrograde(report: PartnerReport, key: str) -> bool:
    return bool(_placement(report, key).get("is_retrograde", False))


def _motion_status(report: PartnerReport, key: str) -> str:
    return str(_placement(report, key).get("motion_status", "stable"))


def _retrograde_label(report: PartnerReport, key: str) -> str:
    if _motion_status(report, key) == "changed_during_day":
        return "смена движения в течение дня (нужно время рождения)"
    return "ретроградное положение" if _is_retrograde(report, key) else "прямое движение"


def _retrograde_note(report: PartnerReport, key: str, label: str) -> str:
    if _motion_status(report, key) == "changed_during_day":
        return f"\n\n↩️ Точность ретроградности ({label}):\nВ этот день планета меняла направление. Без точного времени рождения нельзя честно выбрать один вариант: прямое движение читается как более внешнее проявление, ретроградное — как более внутренняя переработка темы."
    if not _is_retrograde(report, key):
        return ""
    notes = {
        "mercury": (
            "Ретроградный Меркурий усиливает внутреннюю переработку слов: человеку важно время подумать, "
            "перепроверить смысл и возвращаться к теме в бережном тоне. В диалоге лучше задавать ясные вопросы, "
            "фиксировать договорённости и не требовать мгновенной реакции."
        ),
        "venus": (
            "Ретроградная Венера делает тему ценности и симпатии более внутренней: человек может дольше присматриваться, "
            "проверять доверие и возвращаться к старым переживаниям. Лучше не форсировать признания, а показывать стабильную ценность делом."
        ),
        "mars": (
            "Ретроградный Марс разворачивает действие внутрь: импульс может копиться, откладываться или выходить рывками. "
            "Помогает не подгонять, а переводить напряжение в маленький безопасный шаг и понятную границу."
        ),
        "jupiter": (
            "Ретроградный Юпитер показывает рост через личный смысл, а не через внешнюю гонку. Человеку важнее сначала поверить в свой горизонт, "
            "а уже потом расширяться, обещать и брать большой масштаб."
        ),
        "moon": (
            "Ретроградность для Луны практически не используется как отдельный бытовой ключ, поэтому здесь важнее знак, стихия и точность времени рождения."
        ),
    }
    text = notes.get(
        key,
        "Ретроградность делает проявление планеты более внутренним: сначала человек перерабатывает тему внутри, затем проявляет её наружу.",
    )
    return f"\n\n↩️ Ретроградность ({label}):\n{text}"


def _element_name(element: str) -> str:
    return ELEMENT_NAMES.get(element, "свой ритм")


def _basis(report: PartnerReport, key: str, label: str) -> str:
    return f"({label} в {_sign_ru_prepositional(report, key)}, {_element_ru(report, key)}, {_retrograde_label(report, key)})"


def _your_word(label: str) -> str:
    return "ваша" if label in {"Луна", "Венера"} else "ваш"


def _couple_basis(man_report: PartnerReport, woman_report: PartnerReport, key: str, label: str) -> str:
    return f"(его {label} в {_sign_ru_prepositional(man_report, key)}, {_element_ru(man_report, key)}, {_retrograde_label(man_report, key)}; {_your_word(label)} {label} в {_sign_ru_prepositional(woman_report, key)}, {_element_ru(woman_report, key)}, {_retrograde_label(woman_report, key)})"


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
    if key == "jupiter":
        return JUPITER_MEANINGS.get(element, "Рост появляется там, где есть смысл, доверие и понятный горизонт.")
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
    if key == "jupiter":
        return JUPITER_SIGN_DETAILS.get(
            sign,
            "Точный знак Юпитера уточняет, где человеку легче видеть смысл, расти и доверять будущему.",
        )
    return "Точный знак уточняет личный оттенок проявления."


def _expert_lens(key: str) -> str:
    return PLANET_EXPERT_LENS.get(
        key, "Астрологический фокус: смотреть на планету в контексте всей карты и реального поведения."
    )


def _practice_prompt(key: str) -> str:
    return PLANET_PRACTICE_PROMPTS.get(
        key, "Как проверить в жизни: сверять описание с повторяющимися действиями, а не с единичной ситуацией."
    )


def _action_key(report: PartnerReport, key: str) -> str:
    planet_keys = PLANET_ACTION_KEYS.get(key)
    if not planet_keys:
        return ""
    sign = _sign_key(report, key)
    detail = planet_keys.get(sign, planet_keys.get("default", ""))
    if not detail:
        return ""
    return f"\n\nПрактический ключ:\n{detail}"


def _applied_planet_block(report: PartnerReport, key: str, label: str) -> str:
    return (
        f"Профессиональная детализация {label}:\n"
        f"{_expert_lens(key)}\n\n"
        f"Стихия показывает общий режим: {_element_text(report, key)}\n\n"
        f"Знак даёт точный сценарий в поведении ({label} в {_sign_ru_prepositional(report, key)}):\n"
        f"{_sign_detail(report, key)}\n\n"
        f"{_practice_prompt(key)}"
        f"{_retrograde_note(report, key, label)}"
        f"{_action_key(report, key)}"
    )


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


def _variant_options(report: PartnerReport) -> str:
    return " / ".join(_variant_label(item) for item in report.moon_variants) or "два соседних знака Луны"


def _variant_label(variant: dict[str, object]) -> str:
    sign = str(variant.get("sign_ru", "знак не определён"))
    element = str(variant.get("element_ru", "стихия не определена"))
    return f"{sign} ({element})"


def _pair_precision_note(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    changed = []
    if man_report.moon_status == "changed_during_day":
        changed.append(f"его Луна: {_variant_options(man_report)}")
    if woman_report.moon_status == "changed_during_day":
        changed.append(f"ваша Луна: {_variant_options(woman_report)}")
    if not changed:
        return ""
    subject = "; ".join(changed)
    return (
        f"⚠️ Точность Луны: в день рождения могла менять знак: {subject}. "
        "Без времени рождения держим все сценарии — выберите тот, где поведение узнаётся сильнее."
    )


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

{_applied_planet_block(report, "venus", "Венеры")}

🗣 Меркурий — как человек мыслит и договаривается {_basis(report, "mercury", "Меркурий")}:
{MERCURY_SHORT}

{_applied_planet_block(report, "mercury", "Меркурия")}

🔥 Марс — как человек движется и достигает {_basis(report, "mars", "Марс")}:
{MARS_SHORT}

{_applied_planet_block(report, "mars", "Марса")}

Итог:
{_profile_integral(report)}
""".strip()


JUPITER_MEANINGS: dict[str, str] = {
    "fire": "Рост включается через смелость, движение, честную инициативу и ощущение большого живого пути. В паре это про поддержку его желания пробовать, выбирать направление и не терять искру.",
    "earth": "Рост включается через устойчивость, качество, реальные шаги и чувство опоры. В паре это про доверие к плану, деньгам, телу, быту и спокойному накоплению результата.",
    "air": "Рост включается через идеи, разговоры, обучение, связи и свободу мышления. В паре это про пространство для диалога, новых смыслов и совместного интеллектуального горизонта.",
    "water": "Рост включается через чувство, доверие, интуицию, заботу и эмоциональную безопасность. В паре это про атмосферу, где можно раскрыться глубже без стыда.",
}


JUPITER_SIGN_DETAILS: dict[str, str] = {
    "aries": "Юпитер в Овне растёт через смелость, самостоятельность и право начать первым. Его вдохновляет не напор, а доверие к его импульсу.",
    "taurus": "Юпитер в Тельце растёт через качество жизни, тело, устойчивые ресурсы и красивые простые радости. Ему важен рост, который можно почувствовать и удержать.",
    "gemini": "Юпитер в Близнецах растёт через слова, любопытство, обучение и обмен идеями. Его расширяет живая среда, где можно спрашивать, спорить и быстро соединять смыслы.",
    "cancer": "Юпитер в Раке растёт через дом, близость, память, заботу и чувство своей стаи. Ему легче процветать там, где есть эмоциональная опора.",
    "leo": "Юпитер во Льве растёт через признание, творчество, щедрость и личное сияние. Его вдохновляет контакт, где можно быть заметным без унижения и конкуренции.",
    "virgo": "Юпитер в Деве растёт через мастерство, пользу, порядок и улучшение деталей. Его расширяет не шумная мечта, а понятный следующий шаг, который реально работает.",
    "libra": "Юпитер в Весах растёт через партнёрство, красоту обмена, справедливость и умение договариваться. Ему важна гармония, где оба чувствуют ценность.",
    "scorpio": "Юпитер в Скорпионе растёт через глубину, честность, трансформацию и доверие. Поверхностные обещания слабее, чем способность выдерживать настоящие чувства.",
    "sagittarius": "Юпитер в Стрельце растёт через свободу, смысл, путешествие, веру и широкий горизонт. Ему нужна цель больше текущей рутины.",
    "capricorn": "Юпитер в Козероге растёт через зрелость, ответственность, статус и долгую стратегию. Его поддерживает уважение к результату и времени.",
    "aquarius": "Юпитер в Водолее растёт через свободу, дружбу, новые форматы и право быть отдельным. Его вдохновляет не контроль, а совместная идея будущего.",
    "pisces": "Юпитер в Рыбах растёт через мягкость, веру, эмпатию, творчество и тонкое чувство мира. Ему важна атмосфера, где мечта не высмеивается.",
}


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

{MODERN_ASTROLOGER_CONTEXT}

{_expert_lens("moon")}

Его Луна: {_sign_ru(report, "moon")}, стихия {_element_ru(report, "moon")}{precision_block}

Что это значит простыми словами:
{format_moon_person_mechanic(_placement(report, "moon"), role="Его")}{alternate}

{_practice_prompt("moon")}

Что может сбивать контакт {moon_basis}:
{meaning.what_not_to_do}

Мягкий ключ {moon_basis}:
{meaning.first_step}
""".strip()


def format_moon_deep_detail(report: PartnerReport) -> str:
    meaning = MOON_MEANINGS[report.emotional_language]
    sign_detail = MOON_SIGN_DETAILS.get(
        _sign_key(report, "moon"),
        "Точный знак Луны уточняет бытовой формат спокойствия: темп, тон и проявления заботы, которые человек легче принимает.",
    )
    precision_note = format_moon_precision_note(report)
    precision_block = f"\n\n{precision_note}" if precision_note else ""
    alternate = ""
    if report.moon_status == "changed_during_day":
        variant_lines = []
        for variant in _moon_variants(report):
            variant_lines.append(format_moon_person_mechanic(variant, role="Если"))
        alternate = "\n\nЕсли Луна меняла знак в день рождения:\n" + "\n\n".join(variant_lines)
    return f"""
🌙 Луна мужчины глубже: {report.partner_name}

Луна — это место, где мужчина перестаёт держать оборону. Здесь видно, когда ему эмоционально комфортно: в каком темпе он расслабляется, как принимает заботу и рядом с чем начинает наполняться.

Стихия Луны: {_element_ru(report, "moon")}
{meaning.core}

В жизни это выглядит так:
{meaning.how_it_shows}

Когда ему хорошо:
{meaning.needs}

Когда он может закрываться:
{meaning.what_not_to_do}

Луна в знаке: {_sign_ru(report, "moon")}{precision_block}
{sign_detail}

Простые примеры:
• если он устал — сначала дайте подходящий ритм Луны, а уже потом разговор;
• если нужно сблизиться — выбирайте не давление, а формат, где ему безопасно ответить;
• если контакт стал холоднее — проверьте, не стало ли слишком много хаоса, контроля или ожиданий без ясности.

Мягкий ключ:
{meaning.first_step}{alternate}
""".strip()


def format_venus_detail(report: PartnerReport) -> str:
    venus_basis = _basis(report, "venus", "Венера")
    return f"""
💗 Венера — где включаются краски жизни: {report.partner_name}

{VENUS_INTRO}

Венера: {_sign_ru(report, "venus")}, стихия {_element_ru(report, "venus")}, {_retrograde_label(report, "venus")}

{_applied_planet_block(report, "venus", "Венеры")}

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

Меркурий: {_sign_ru(report, "mercury")}, стихия {_element_ru(report, "mercury")}, {_retrograde_label(report, "mercury")}

{_applied_planet_block(report, "mercury", "Меркурия")}

Что особенно важно {mercury_basis}:
не только подобрать правильные слова, но и попасть в способ мышления: темп, тон, прямоту, мягкость, факты или структуру.

Мягкий ключ:
начинать не с напора, а с намерения: «Я хочу понять, как ты это видишь».
""".strip()


def format_mars_detail(report: PartnerReport) -> str:
    mars_basis = _basis(report, "mars", "Марс")
    return f"""
🔥 Марс — как человек движется и достигает: {report.partner_name}

{MARS_INTRO}

Марс: {_sign_ru(report, "mars")}, стихия {_element_ru(report, "mars")}, {_retrograde_label(report, "mars")}

{_applied_planet_block(report, "mars", "Марса")}

Что особенно важно {mars_basis}:
в напряжении человек часто показывает не только характер, но и способ двигаться к желаемому, защищать своё направление и действовать в напряжении.

Мягкий ключ:
не тянуть силой в свой темп, а понять, как человек движется, достигает и где ему нужен понятный следующий шаг.
""".strip()


def format_jupiter_detail(report: PartnerReport) -> str:
    jupiter_basis = _basis(report, "jupiter", "Юпитер")
    return f"""
🪐 Юпитер — где у человека включается рост и большое доверие: {report.partner_name}

Юпитер в таком разборе — не про обещание удачи, а про направление расширения: где человеку легче верить в себя, видеть смысл, расти, щедрее относиться к жизни и строить общий горизонт.

Юпитер: {_sign_ru(report, "jupiter")}, стихия {_element_ru(report, "jupiter")}, {_retrograde_label(report, "jupiter")}

Стихийная база:
{_element_text(report, "jupiter")}

Точный оттенок знака:
{_sign_detail(report, "jupiter")}{_retrograde_note(report, "jupiter", "Юпитера")}

Что особенно важно {jupiter_basis}:
не проталкивать человека мотивацией, а увидеть, где у него естественно появляется вера, щедрость, интерес к будущему и желание расти рядом.

Мягкий ключ:
спросить не «почему ты не делаешь больше?», а «какой следующий горизонт тебе сейчас правда интересен — и как я могу поддержать его без контроля?».
""".strip()


def format_planet_short_card(report: PartnerReport, key: str) -> str:
    labels = {
        "moon": ("🌙", "Луна", "как стать его тихой гаванью"),
        "venus": ("💗", "Венера", "как включить его нежность"),
        "mercury": ("🗣", "Меркурий", "слова, которые он слышит"),
        "mars": ("🔥", "Марс", "как дать ему силу действовать"),
        "jupiter": ("🪐", "Юпитер", "куда вести вашу пару"),
    }
    emoji, title, promise = labels.get(key, ("✨", "Карта", "главный ключ"))
    if key == "moon":
        action = MOON_MEANINGS[report.emotional_language].first_step
    elif key == "jupiter":
        action = "поддерживать не напором, а вопросом о честном следующем горизонте и понятном маленьком шаге."
    else:
        action = _action_key(report, key).replace("\n\nПрактический ключ:\n", "") or _practice_prompt(key)
    return f"""
{emoji} {title}: главное для жизни

{report.partner_name}: {title} в {_sign_ru(report, key)}, стихия {_element_ru(report, key)}, {_retrograde_label(report, key)}.

Короткий ключ: {promise} — через его реальный ритм, а не через угадывание.

Что сделать сейчас:
{action}{_retrograde_note(report, key, title)}

👇 Подробный красивый разбор с примерами откройте по кнопке ниже.
""".strip()


def format_couple_portraits_short_card(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    return f"""
👤 Портреты в отношениях: главное

Он: Луна в {_sign_ru(man_report, "moon")} — ему важен ритм «{_element_ru(man_report, "moon")}».
Вы: Луна в {_sign_ru(woman_report, "moon")} — вам важен ритм «{_element_ru(woman_report, "moon")}».

Короткий ключ: не становиться одинаковыми, а понять, что наполняет каждого — где нужен покой, где тепло, где слова, а где действие.

Что сделать сейчас:
выберите один маленький мост на сегодня: «что даст тебе спокойствие?» + «что даст мне тепло?».

👇 Подробные портреты с яркими подсказками и применением в жизни откройте по кнопке ниже.
""".strip()


def format_couple_moon_bridge_short_card(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    """Short Telegram card that sends users to the full HTML bridge."""
    precision_note = _pair_precision_note(man_report, woman_report)
    precision_line = (
        "\n\nТехническое уточнение: если Луна была на переходе, в полной версии можно свайпнуть варианты и выбрать похожий на жизнь."
        if precision_note
        else ""
    )
    return f"""
💞 Эмоциональный мост: главное

{_moon_pair_title(man_report, woman_report)}

Коротко: это инструкция к любимому мужчине без режима «угадай, что я имела в виду». Сначала даём ему понятный сигнал спокойствия, потом мягко называем своё тепло — и смотрим, становится ли между вами легче.

Что сделать сейчас:
1. Дайте ему его формат безопасности: темп, тон или конкретику.
2. Одной фразой скажите, что делает теплее вам.
3. Проверьте реакцию: он расслабился, ответил яснее или сделал шаг навстречу? Значит, мост работает.{precision_line}

👇 Полную карту моста с развёрнутыми вариантами Луны откройте по кнопке ниже.
""".strip()


def format_moon_variant_cards(man_report: PartnerReport, woman_report: PartnerReport) -> list[dict[str, str]]:
    """Moon transition combinations for a swipe UI in the WebApp."""
    cards: list[dict[str, str]] = []
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
            title = f"Он: {_variant_label(man_variant)} · Вы: {_variant_label(woman_variant)}"
            cards.append(
                {
                    "title": title,
                    "text": format_moon_variant_pair(man_variant, woman_variant),
                }
            )
    return cards


def format_couple_moon_bridge(
    man_report: PartnerReport, woman_report: PartnerReport, *, include_transition_variants: bool = True
) -> str:
    precision_note = _pair_precision_note(man_report, woman_report)
    precision_block = f"\n\n{precision_note}" if precision_note else ""
    mechanic = format_moon_pair_mechanic(_placement(man_report, "moon"), _placement(woman_report, "moon"))
    alternate_block = _alternate_moon_bridge_block(man_report, woman_report) if include_transition_variants else ""
    alternate_text = f"\n\n{alternate_block}" if alternate_block else ""
    return f"""
💞 Ваш эмоциональный мост

{_moon_pair_title(man_report, woman_report)}{precision_block}

Что вы сейчас открыли:
это не «совместимы / не совместимы», а эмоциональная карта входа друг к другу. Она помогает понять, какой тон, темп и первый шаг снижают защиту мужчины, не обесценивая ваши чувства.

{mechanic}

{_element_background(man_report, woman_report)}{alternate_text}

Как пользоваться этим мостом ближайшие 24 часа:
• выберите один маленький разговор, а не генеральную ревизию отношений;
• начните с его формата безопасности, но обязательно назовите свою потребность;
• завершите конкретным шагом: время, действие, пауза, сообщение или договорённость;
• после контакта отметьте факт: стало ли больше спокойствия, ясности и тепла.

Гармония здесь не в том, чтобы кто-то стал удобнее. Она в том, чтобы перестать читать мысли по аватарке и собрать живую инструкцию: что даёт ему спокойствие, что даёт вам тепло и какой маленький шаг можно сделать без давления.
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
    jupiter_basis = _couple_basis(man_report, woman_report, "jupiter", "Юпитер")
    mechanic = format_moon_pair_mechanic(_placement(man_report, "moon"), _placement(woman_report, "moon"))
    alternate_block = _alternate_moon_bridge_block(man_report, woman_report)
    alternate_text = f"\n\n{alternate_block}" if alternate_block else ""
    return f"""
📖 Карта гармонии пары: {man_report.partner_name} + {woman_report.partner_name}

Эта карта не говорит, подходите вы друг другу или нет. Она показывает, какой эмоциональный ритм возникает между вами и как перевести разницу реакций в понятную инструкцию к любимому мужчине: больше тепла, ясности, доверия и меньше гадания на синих галочках.

{MODERN_ASTROLOGER_CONTEXT}

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
{_sign_detail(man_report, "venus")}{_retrograde_note(man_report, "venus", "его Венера")}

Ваша Венера: {_sign_ru(woman_report, "venus")}, стихия {_element_ru(woman_report, "venus")}
Стихийная база: {_element_text(woman_report, "venus")}
Точный оттенок вашей Венеры в {_sign_ru(woman_report, "venus")}:
{_sign_detail(woman_report, "venus")}{_retrograde_note(woman_report, "venus", "ваша Венера")}

Здесь важно не копировать чужой способ любить, а почувствовать, где у каждого включаются краски жизни, ценность и притяжение.

🗣 Меркурий — как человек мыслит и договаривается {mercury_basis}
{MERCURY_SHORT}

Его Меркурий: {_sign_ru(man_report, "mercury")}, стихия {_element_ru(man_report, "mercury")}
Стихийная база: {_element_text(man_report, "mercury")}
Точный оттенок его Меркурия в {_sign_ru(man_report, "mercury")}:
{_sign_detail(man_report, "mercury")}{_retrograde_note(man_report, "mercury", "его Меркурий")}

Ваш Меркурий: {_sign_ru(woman_report, "mercury")}, стихия {_element_ru(woman_report, "mercury")}
Стихийная база: {_element_text(woman_report, "mercury")}
Точный оттенок вашего Меркурия в {_sign_ru(woman_report, "mercury")}:
{_sign_detail(woman_report, "mercury")}{_retrograde_note(woman_report, "mercury", "ваш Меркурий")}

Слова становятся мостом, когда они учитывают не только тему разговора, но и способ мышления человека.

🔥 Марс — как человек движется и достигает {mars_basis}
{MARS_SHORT}

Его Марс: {_sign_ru(man_report, "mars")}, стихия {_element_ru(man_report, "mars")}
Стихийная база: {_element_text(man_report, "mars")}
Точный оттенок его Марса в {_sign_ru(man_report, "mars")}:
{_sign_detail(man_report, "mars")}{_retrograde_note(man_report, "mars", "его Марс")}

Ваш Марс: {_sign_ru(woman_report, "mars")}, стихия {_element_ru(woman_report, "mars")}
Стихийная база: {_element_text(woman_report, "mars")}
Точный оттенок вашего Марса в {_sign_ru(woman_report, "mars")}:
{_sign_detail(woman_report, "mars")}{_retrograde_note(woman_report, "mars", "ваш Марс")}

Напряжение не обязательно разрушает пару. Иногда оно просто показывает, что два ритма движения пока не нашли общий шаг.

🪐 Юпитер — общий горизонт роста {jupiter_basis}
Его Юпитер: {_sign_ru(man_report, "jupiter")}, стихия {_element_ru(man_report, "jupiter")}
{_sign_detail(man_report, "jupiter")}{_retrograde_note(man_report, "jupiter", "его Юпитер")}

Ваш Юпитер: {_sign_ru(woman_report, "jupiter")}, стихия {_element_ru(woman_report, "jupiter")}
{_sign_detail(woman_report, "jupiter")}{_retrograde_note(woman_report, "jupiter", "ваш Юпитер")}

Этот блок показывает не «кто успешнее», а где каждому легче видеть смысл, расширять жизнь и поддерживать общий горизонт в спокойном темпе.

Мягкий вывод:
Гармония здесь не в том, чтобы стать одинаковыми. Она в том, чтобы распознать ритм друг друга и перестать воевать с тем, что на самом деле просит понимания. Лучший следующий шаг — не большой разговор «обо всём», а один маленький мост: что я могу дать тебе для спокойствия и что мне важно получить для тепла.
""".strip()


def format_full_report_intro(report: PartnerReport) -> str:
    return f"""
📖 Карта гармонии пары

Чтобы собрать карту пары, нужна не только дата мужчины, но и ваша дата рождения.

Сейчас открыт разбор {report.partner_name}. Добавьте свою дату, чтобы увидеть общий эмоциональный ритм: где ему спокойнее, где живее вам, и какой мост может появиться между вами.
""".strip()
