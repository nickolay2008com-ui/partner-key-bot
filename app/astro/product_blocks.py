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
from app.astro.report import PartnerReport, format_moon_precision_note


ELEMENT_KEYWORDS = {
    "fire": "живость, отклик, движение, интерес",
    "earth": "спокойствие, тело, надёжность, понятность",
    "air": "разговор, лёгкость, ясность, пространство",
    "water": "мягкость, чувство, принятие, безопасность",
}


ELEMENT_TEXT = {
    "fire": (
        "Такой человек чаще раскрывается не через тяжёлую серьёзность и долгие выяснения, "
        "а через ощущение: рядом есть жизнь, искра, желание двигаться навстречу.\n\n"
        "Ему легче становиться ближе, когда контакт не тухнет и не превращается в обязанность, "
        "а остаётся живым и тёплым."
    ),
    "earth": (
        "Такой человек чаще раскрывается не через вспышки и громкие признания, "
        "а через ощущение: рядом устойчиво, спокойно, можно расслабиться.\n\n"
        "Ему легче становиться ближе, когда контакт не качает из стороны в сторону, "
        "а становится тёплым и надёжным."
    ),
    "air": (
        "Такой человек чаще раскрывается не через давление на глубину, "
        "а через ощущение: рядом можно говорить, думать, шутить, дышать и не быть зажатым.\n\n"
        "Ему легче становиться ближе, когда контакт не становится клеткой, "
        "а оставляет место для живого обмена."
    ),
    "water": (
        "Такой человек чаще раскрывается не через прямой нажим и холодную логику, "
        "а через ощущение: меня чувствуют, меня не торопят, рядом можно быть уязвимым.\n\n"
        "Ему легче становиться ближе, когда слова звучат не только правильно, но и тепло."
    ),
}


YOU_ELEMENT_TEXT = {
    "fire": (
        "Вам легче чувствовать контакт, когда в нём есть живость, отклик и движение. "
        "Важно ощущать, что связь не стоит на месте и в ней остаётся искра."
    ),
    "earth": (
        "Вам легче чувствовать контакт, когда рядом спокойно, понятно и надёжно. "
        "Важно ощущать, что связь не качает из стороны в сторону, а становится устойчивой."
    ),
    "air": (
        "Вам легче чувствовать контакт, когда можно говорить свободно, ясно и без внутренней тесноты. "
        "Важно, чтобы между вами оставалось пространство для живого обмена."
    ),
    "water": (
        "Вам легче чувствовать контакт, когда есть мягкость, принятие и эмоциональная безопасность. "
        "Важно ощущать, что чувства не обесценивают и не торопят."
    ),
}


MOON_INTRO = (
    "Луна показывает, где человеку становится спокойно внутри.\n\n"
    "Это не просто эмоции и настроение. Это базовый способ чувствовать безопасность, восстанавливаться, доверять, "
    "расслабляться и быть живым без лишнего напряжения.\n\n"
    "В отношениях Луна показывает базу близости: какая атмосфера раскрывает человека, что его закрывает, "
    "где ему нужен покой, забота, пространство, движение или мягкий отклик.\n\n"
    "В процветании Луна показывает способность держать внутренний ресурс: восстанавливаться, не перегреваться, "
    "чувствовать свой ритм и не терять устойчивость в период перемен.\n\n"
    "Чтобы понять партнёра, Луна отвечает на вопрос: где ему спокойно быть собой?"
)


VENUS_INTRO = (
    "Венера показывает, где у человека включаются краски жизни.\n\n"
    "Это точка ценности, вкуса, удовольствия, выбора, красоты, денег, обмена, притяжения и способности принимать лучшее.\n\n"
    "В отношениях Венера показывает, что человеку приятно, что он считает красивым и ценным, как чувствует симпатию, "
    "через что тянется ближе и какие проявления любви действительно попадают в него.\n\n"
    "В процветании Венера показывает, как приходит процветание: за счёт чего человек становится привлекательным, "
    "желанным, выбираемым и ценным для других. Где его вкус, стиль, мягкость, качество, эстетика или особая атмосфера "
    "превращаются в притяжение и обмен.\n\n"
    "Чтобы понять партнёра, Венера отвечает на вопрос: где у него включаются удовольствие, ценность и живое притяжение?"
)


MERCURY_INTRO = (
    "Меркурий показывает, как человек мыслит, слышит, объясняет, пишет, спорит, учится, задаёт вопросы, "
    "ведёт переговоры и оформляет смысл словами.\n\n"
    "В отношениях Меркурий показывает, через какой язык к человеку можно войти в понимание: где ему нужна логика, "
    "где мягкость, где прямота, где факты, где время подумать, а где живой диалог.\n\n"
    "В процветании Меркурий связан с переговорами, сделками, обучением, перепиской, объяснением ценности, "
    "продажей идей и способностью находить общий язык с людьми, рынком и обстоятельствами.\n\n"
    "Чтобы понять партнёра, Меркурий отвечает на вопрос: как он думает, слышит, объясняет и договаривается с миром?"
)


MARS_INTRO = (
    "Марс показывает, как человек хочет, движется, действует, спорит, защищается, проявляет напор, "
    "сексуальность, инициативу, границы и способность брать.\n\n"
    "В отношениях Марс показывает, как человек делает шаг, как проявляет желание, как реагирует на сопротивление, "
    "где становится резким, как защищает своё направление и что включает в нём активное действие.\n\n"
    "В процветании Марс показывает способность достигать: идти к цели, конкурировать, выдерживать напряжение, "
    "принимать вызов, действовать в реальности и не оставлять желание только в фантазии.\n\n"
    "Чтобы понять партнёра, Марс отвечает на вопрос: как он движется к желаемому, как берёт своё и как действует под давлением?"
)


MOON_SHORT = "Луна показывает, где человеку спокойно внутри и какая атмосфера помогает ему раскрыться без лишнего напряжения."
VENUS_SHORT = "Венера показывает, где включаются краски жизни: ценность, вкус, притяжение, обмен и способность принимать лучшее."
MERCURY_SHORT = "Меркурий показывает, как человек мыслит, слышит, объясняет, ведёт переговоры и договаривается с миром."
MARS_SHORT = "Марс показывает, как человек движется, хочет, действует, защищается, берёт своё и достигает."


BRIDGE_MAP = {
    ("fire", "fire"): ("Огонь и Огонь: живость + живость", "Оба ритма ищут отклик, движение и внутренний огонь. Здесь много жизни, но важно не превращать искру в постоянные вспышки.", "Мост между вами — живость, у которой есть бережная форма."),
    ("fire", "earth"): ("Огонь и Земля: живость + устойчивость", "Ему легче через движение и отклик, вам — через спокойствие и надёжность. Один ритм ищет искру, другой — землю под ногами.", "Мост между вами — живой контакт, который не теряет опору."),
    ("fire", "air"): ("Огонь и Воздух: движение + разговор", "Один ритм загорается через действие, другой — через лёгкость и слова. Вместе это может давать живой обмен, если разговор не заменяет движение.", "Мост между вами — интерес, который становится шагом навстречу."),
    ("fire", "water"): ("Огонь и Вода: искра + мягкость", "Один ритм хочет быстрого отклика, другой раскрывается бережнее. Здесь важно не путать мягкость с холодом, а импульс — с давлением.", "Мост между вами — живость, в которой есть тепло и аккуратность."),
    ("earth", "fire"): ("Земля и Огонь: устойчивость + живость", "Ему легче через спокойствие и надёжность, вам — через движение и живой отклик. Он может искать опору, а вы можете ждать больше импульса.", "Мост между вами — спокойная основа, в которой есть искра."),
    ("earth", "earth"): ("Земля и Земля: устойчивость + устойчивость", "Оба ритма ищут спокойствие, понятность и надёжность. Здесь тепло часто растёт не на словах, а через присутствие и повторяемость.", "Мост между вами — стабильность, которая остаётся живой, а не просто привычной."),
    ("earth", "air"): ("Земля и Воздух: опора + пространство", "Один ритм ищет понятность и надёжность, другой — лёгкость, разговор и воздух. Здесь слова могут казаться слишком лёгкими, а молчаливая устойчивость — слишком закрытой.", "Мост между вами — ясность, которая становится действием."),
    ("earth", "water"): ("Земля и Вода: опора + мягкость", "Один ритм даёт спокойствие, другой ищет эмоциональное тепло. Вместе это может стать очень тёплой связкой, если действия не остаются без чувства, а чувства не теряют опору.", "Мост между вами — надёжность, в которой есть мягкость."),
    ("air", "fire"): ("Воздух и Огонь: разговор + движение", "Ему легче через лёгкость, слова и пространство, вам — через живой отклик и движение. Здесь важно, чтобы разговор не зависал, а импульс не сжигал диалог.", "Мост между вами — разговор, который становится живым шагом."),
    ("air", "earth"): ("Воздух и Земля: ясность + надёжность", "Ему легче через разговор и пространство, вам — через устойчивость и конкретику. Один ритм хочет объяснить, другой — почувствовать надёжность.", "Мост между вами — слова, которые подтверждаются спокойным действием."),
    ("air", "air"): ("Воздух и Воздух: лёгкость + лёгкость", "Оба ритма ищут разговор, пространство и живой обмен. Здесь может быть много понимания через слова, юмор и мысли.", "Мост между вами — лёгкость, которая не растворяется в одних разговорах."),
    ("air", "water"): ("Воздух и Вода: ясность + чувство", "Один ритм ищет слова и пространство, другой — мягкость и эмоциональную безопасность. Здесь важно, чтобы ясность не звучала холодно, а чувство не превращалось в туман.", "Мост между вами — тёплая ясность."),
    ("water", "fire"): ("Вода и Огонь: мягкость + живость", "Ему легче через чувство и бережность, вам — через отклик и движение. Один ритм раскрывается глубже, другой хочет быстрее почувствовать жизнь в контакте.", "Мост между вами — искра, которая не пугает, а согревает."),
    ("water", "earth"): ("Вода и Земля: чувство + опора", "Ему легче через мягкость и принятие, вам — через спокойствие и надёжность. Здесь чувства получают форму, а стабильность становится теплее.", "Мост между вами — забота, в которой есть и чувство, и реальность."),
    ("water", "air"): ("Вода и Воздух: чувство + ясность", "Ему легче через мягкость и эмоциональную безопасность, вам — через разговор и пространство. Здесь важно не принимать ясность за холод, а чувство — за драму.", "Мост между вами — слова, в которых есть бережность."),
    ("water", "water"): ("Вода и Вода: чувство + чувство", "Оба ритма ищут мягкость, принятие и эмоциональную безопасность. Здесь многое может пониматься без слов, через тон, паузу и настроение.", "Мост между вами — чувство, у которого есть спокойный берег."),
}


COUPLE_DIAGNOSTICS = {
    ("fire", "fire"): ("Вы быстро оживляете друг друга. В такой паре много энергии, реакции, желания действовать и не застревать в тяжёлых паузах.", "Контакт может перегреваться: оба могут ждать мгновенного отклика, резко реагировать и путать живость с борьбой за внимание.", "Сохранять искру, но вводить паузу перед резкими словами. Лучше договариваться о следующем шаге, чем выяснять, кто ярче горит."),
    ("fire", "earth"): ("Вы можете соединить движение и надёжность: один даёт импульс, другой помогает контакту не рассыпаться и стать реальным.", "Один может хотеть быстрого отклика, а другой раскрываться медленнее. Из-за этого живость может казаться давлением, а спокойствие — холодом.", "Делать шаги живо, но не резко. Давать инициативу, но оставлять человеку время почувствовать устойчивость."),
    ("fire", "air"): ("У вас может быть лёгкий, живой, интересный контакт: идеи быстро превращаются в движение, а разговор не даёт связи застаиваться.", "Можно много загораться, обсуждать и обещать, но терять глубину или конкретный следующий шаг.", "После живого разговора фиксировать простое действие: встречу, звонок, прогулку, маленькую договорённость."),
    ("fire", "water"): ("Вы можете соединить искру и нежность: один оживляет контакт, другой делает его глубже и эмоциональнее.", "Быстрый импульс может пугать более чувствительный ритм, а мягкость может восприниматься как неопределённость или отстранение.", "Добавлять тепло к инициативе. Не торопить чувство, но и не оставлять контакт в тумане."),
    ("earth", "fire"): ("Вы можете соединить опору и движение: один создаёт стабильность, другой возвращает в контакт жизнь и интерес.", "Один может хотеть спокойного темпа, а другой ждать быстрой реакции. Тогда надёжность кажется скукой, а живость — лишней суетой.", "Сначала дать ощущение безопасности, потом добавлять движение. Не ломать ритм резкостью, но и не давать связи заснуть."),
    ("earth", "earth"): ("Ваша сильная сторона — надёжность. Тепло здесь растёт через поступки, повторяемость, заботу и ощущение, что рядом можно расслабиться.", "Главный риск — привыкнуть к стабильности и перестать оживлять контакт. Тогда тепло может стать фоном, который уже не замечают.", "Сохранять понятность, но добавлять маленькие живые жесты: прогулки, прикосновения, совместные планы, простые приятные ритуалы."),
    ("earth", "air"): ("Вы можете соединить конкретику и ясность: один помогает сделать контакт надёжным, другой — проговорить то, что иначе осталось бы в молчании.", "Один может ждать дел и устойчивости, другой — разговора и пространства. Тогда слова кажутся пустыми, а молчание — закрытостью.", "Переводить слова в маленькие действия, а действия — в понятные слова. Не требовать, чтобы другой угадывал без объяснения."),
    ("earth", "water"): ("Это мягкая и тёплая связка: один даёт опору, другой добавляет чувство. Вместе можно создавать ощущение дома и эмоциональной безопасности.", "Если действия остаются без слов, чувствительному ритму может не хватать тепла. Если чувства становятся слишком зыбкими, земному ритму может не хватать ясности.", "Соединять заботу делом и заботу словом. Не выбирать между стабильностью и нежностью, а давать им работать вместе."),
    ("air", "fire"): ("У вас может быть много живого обмена: разговоры быстро оживляют контакт, а импульс помогает не оставаться только в мыслях.", "Можно спорить ради энергии, уходить в резкие слова или быстро перескакивать с темы на тему, не доходя до настоящей близости.", "Сохранять лёгкость, но не превращать контакт в соревнование реакций. После разговора выбирать один понятный шаг."),
    ("air", "earth"): ("Вы можете соединить ясность и устойчивость: один помогает говорить, другой — делать связь надёжной и спокойной.", "Один может искать объяснения и свободу, другой — конкретику и предсказуемость. Из-за этого разговор может казаться уходом от дела, а устойчивость — давлением.", "Давать словам форму: договорённости, планы, простые подтверждения. И давать делам голос: объяснять, что за ними стоит."),
    ("air", "air"): ("Ваша сильная сторона — лёгкость понимания. Вы можете сближаться через разговор, юмор, мысли, переписку и ощущение внутреннего пространства.", "Главный риск — остаться в словах и не дать контакту глубины, тела, устойчивости или эмоционального подтверждения.", "Оставлять воздух, но добавлять присутствие: не только говорить о близости, но и показывать её действиями, временем и вниманием."),
    ("air", "water"): ("Вы можете соединить ясность и чувство: один помогает назвать происходящее, другой — вернуть словам тепло и эмоциональную глубину.", "Ясность может звучать слишком холодно, а чувство — слишком размыто. Тогда один просит объяснить, другой хочет, чтобы его просто почувствовали.", "Говорить мягче и чувствовать яснее. Лучше прямо называть важное, но тоном, в котором есть бережность."),
    ("water", "fire"): ("Вы можете соединить глубину и искру: один даёт эмоциональную включённость, другой помогает контакту оживать и двигаться.", "Чувствительность может закрываться от резкости, а живой импульс может раздражаться от долгой неопределённости.", "Давать инициативу через тепло, а чувства — через ясные сигналы. Не давить скоростью и не исчезать в настроении."),
    ("water", "earth"): ("Вы можете создать очень тёплую опору: чувство получает форму, а стабильность становится не сухой, а живой и заботливой.", "Если земной ритм молчит и просто делает, водный может не чувствовать тепла. Если водный ритм уходит в переживания, земной может терять понятность.", "Подтверждать любовь и делом, и тоном. Простая забота плюс мягкие слова здесь работают сильнее громких драм."),
    ("water", "air"): ("Вы можете соединить чувство и понимание: один тонко улавливает атмосферу, другой помогает не тонуть в догадках и проговаривать важное.", "Один может ждать эмоционального считывания, другой — ясных слов. Тогда молчание становится тревогой, а объяснения кажутся недостаточно тёплыми.", "Не заставлять угадывать. Говорить прямо, но бережно: что чувствуется, что важно, какой маленький шаг поможет сейчас."),
    ("water", "water"): ("Ваша сильная сторона — эмоциональная тонкость. Вы можете чувствовать настроение друг друга без лишних объяснений и создавать глубокое тепло.", "Главный риск — утонуть в настроениях, обидах и недосказанности. Когда оба чувствительны, тишина может становиться слишком громкой.", "Давать чувствам спокойный берег: мягко проговаривать важное, не копить обиды и не проверять любовь молчанием."),
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


def _element_name(element: str) -> str:
    return {"fire": "Огонь", "earth": "Земля", "air": "Воздух", "water": "Вода"}.get(element, "свой ритм")


def _basis(report: PartnerReport, key: str, label: str) -> str:
    return f"({label} в {_sign_ru(report, key)}, {_element_ru(report, key)})"


def _your_word(label: str) -> str:
    return "ваша" if label in {"Луна", "Венера"} else "ваш"


def _couple_basis(man_report: PartnerReport, woman_report: PartnerReport, key: str, label: str) -> str:
    return f"(его {label} в {_sign_ru(man_report, key)}, {_element_ru(man_report, key)}; {_your_word(label)} {label} в {_sign_ru(woman_report, key)}, {_element_ru(woman_report, key)})"


def _rhythm_for_man(element: str, basis: str = "") -> str:
    keywords = ELEMENT_KEYWORDS.get(element, "свой ритм, близость, спокойствие, контакт")
    text = ELEMENT_TEXT.get(element, "Такому человеку легче раскрываться в атмосфере, где его не давят и не торопят.")
    basis_text = f" {basis}" if basis else ""
    return f"Его эмоциональный ритм — {_element_name(element)}{basis_text}: {keywords}.\n\n{text}"


def _rhythm_for_you(element: str, basis: str = "") -> str:
    keywords = ELEMENT_KEYWORDS.get(element, "свой ритм, близость, спокойствие, контакт")
    text = YOU_ELEMENT_TEXT.get(element, "Вам легче чувствовать контакт, когда рядом есть уважение к вашему способу быть ближе.")
    basis_text = f" {basis}" if basis else ""
    return f"Ваш эмоциональный ритм — {_element_name(element)}{basis_text}: {keywords}.\n\n{text}"


def _bridge_for(left: str, right: str) -> tuple[str, str, str]:
    return BRIDGE_MAP.get((left, right), ("Общий ритм", "Между вами встречаются два способа искать тепло и близость.", "Мост между вами — не делать друг друга одинаковыми, а найти ритм, где обоим легче быть рядом."))


def _diagnostics_for(left: str, right: str) -> tuple[str, str, str]:
    return COUPLE_DIAGNOSTICS.get((left, right), (
        "Вы можете заметить, что у каждого есть свой способ искать близость. Уже это понимание снижает лишнее напряжение.",
        "Контакт может теряться там, где один ждёт одного формата тепла, а другой показывает его совсем иначе.",
        "Не пытаться сделать друг друга одинаковыми. Лучше назвать два ритма и найти один маленький шаг, где обоим легче быть рядом.",
    ))


def _pair_precision_note(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    notes = [format_moon_precision_note(item) for item in (man_report, woman_report)]
    notes = [item for item in notes if item]
    if not notes:
        return ""
    return "\n\n".join(notes)


def _element_text(report: PartnerReport, key: str) -> str:
    element = _element(report, key)
    if key == "venus":
        return VENUS_MEANINGS.get(element, "Тепло появляется через внимание, ценность, вкус и естественное притяжение.")
    if key == "mercury":
        return MERCURY_MEANINGS.get(element, "Слова лучше слышатся, когда в них есть спокойствие и ясность.")
    if key == "mars":
        return MARS_MEANINGS.get(element, "В напряжении помогает вернуть ясность и уважение к темпу.")
    return MOON_MEANINGS[report.emotional_language].needs


def _sign_detail(report: PartnerReport, key: str) -> str:
    sign = _sign_key(report, key)
    if key == "moon":
        return MOON_SIGN_DETAILS.get(sign, "Точный знак Луны уточняет, какой формат эмоционального спокойствия человеку ближе.")
    if key == "venus":
        return VENUS_SIGN_DETAILS.get(sign, "Точный знак Венеры уточняет, где у человека включаются ценность, вкус и притяжение.")
    if key == "mercury":
        return MERCURY_SIGN_DETAILS.get(sign, "Точный знак Меркурия уточняет, как человеку легче мыслить, слышать слова и входить в договорённость.")
    if key == "mars":
        return MARS_SIGN_DETAILS.get(sign, "Точный знак Марса уточняет, как человек движется, действует и защищает своё направление.")
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


def _variant_sign_ru(variant: dict[str, object]) -> str:
    return str(variant.get("sign_ru", "не определён"))


def _variant_element(variant: dict[str, object]) -> str:
    return str(variant.get("element", ""))


def _variant_element_ru(variant: dict[str, object]) -> str:
    return str(variant.get("element_ru", ""))


def _variant_basis(man_variant: dict[str, object], woman_variant: dict[str, object]) -> str:
    return (
        f"его Луна в {_variant_sign_ru(man_variant)}, {_variant_element_ru(man_variant)}; "
        f"ваша Луна в {_variant_sign_ru(woman_variant)}, {_variant_element_ru(woman_variant)}"
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
            left = _variant_element(man_variant)
            right = _variant_element(woman_variant)
            key = (str(man_variant.get("sign_key", "")), left, str(woman_variant.get("sign_key", "")), right)
            if key in seen:
                continue
            seen.add(key)
            title, tension, bridge = _bridge_for(left, right)
            strength, loss, soft_key = _diagnostics_for(left, right)
            basis = _variant_basis(man_variant, woman_variant)
            lines.append(
                f"\nЕсли {basis}:\n"
                f"{title}\n"
                f"Сильная сторона: {strength}\n"
                f"Где может теряться контакт: {loss}\n"
                f"Мягкий ключ: {soft_key}\n"
                f"{bridge}"
            )
    return "\n\n".join(lines).strip()


def _profile_integral(report: PartnerReport) -> str:
    moon = f"Луна в {_sign_ru(report, 'moon')} — {_element_ru(report, 'moon')}"
    venus = f"Венера в {_sign_ru(report, 'venus')} — {_element_ru(report, 'venus')}"
    mercury = f"Меркурий в {_sign_ru(report, 'mercury')} — {_element_ru(report, 'mercury')}"
    mars = f"Марс в {_sign_ru(report, 'mars')} — {_element_ru(report, 'mars')}"
    return (
        f"Связка карты: {moon}; {venus}; {mercury}; {mars}. "
        "Поэтому человека лучше понимать не по одному признаку, а по сочетанию: где ему спокойно, "
        "где включаются краски жизни, как он мыслит и как движется к желаемому."
    )


def _person_deep_profile(report: PartnerReport, title: str) -> str:
    moon_meaning = MOON_MEANINGS[report.emotional_language]
    return f"""
{title}: подробнее

🌙 Луна — где человеку спокойно {_basis(report, "moon", "Луна")}:
{MOON_SHORT}

Стихийная база: {moon_meaning.needs}

Точный оттенок Луны в {_sign_ru(report, "moon")}:
{_sign_detail(report, "moon")}

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
            sign_key = str(variant.get("sign_key", ""))
            element = str(variant.get("element", report.emotional_language))
            sign_ru = _variant_sign_ru(variant)
            element_ru = _variant_element_ru(variant)
            meaning_variant = MOON_MEANINGS.get(element, meaning)
            sign_detail = MOON_SIGN_DETAILS.get(sign_key, "Этот вариант Луны уточняет, какой эмоциональный ритм человеку ближе.")
            variant_lines.append(
                f"Если Луна в {sign_ru}, {element_ru}:\n"
                f"Стихийный ритм: {meaning_variant.needs}\n"
                f"Точный оттенок: {sign_detail}"
            )
        alternate = "\n\nВозможные варианты Луны без точного времени рождения:\n" + "\n\n".join(variant_lines)
    return f"""
🌙 Луна — где человеку спокойно: {report.partner_name}

{MOON_INTRO}

Луна: {_sign_ru(report, "moon")}, стихия {_element_ru(report, "moon")}{precision_block}

{_rhythm_for_man(report.emotional_language, moon_basis)}

Точный оттенок Луны в {_sign_ru(report, "moon")}:
{_sign_detail(report, "moon")}{alternate}

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
    title, tension, bridge = _bridge_for(man_report.emotional_language, woman_report.emotional_language)
    strength, loss, key = _diagnostics_for(man_report.emotional_language, woman_report.emotional_language)
    precision_note = _pair_precision_note(man_report, woman_report)
    precision_block = f"\n\n{precision_note}" if precision_note else ""
    moon_basis = _couple_basis(man_report, woman_report, "moon", "Луна")
    alternate_block = _alternate_moon_bridge_block(man_report, woman_report)
    alternate_text = f"\n\n{alternate_block}" if alternate_block else ""
    return f"""
💞 Ваш эмоциональный мост

{title} {moon_basis}{precision_block}

{_rhythm_for_man(man_report.emotional_language, _basis(man_report, "moon", "Луна"))}

{_rhythm_for_you(woman_report.emotional_language, _basis(woman_report, "moon", "Луна"))}

Сильная сторона вашей пары {moon_basis}:
{strength}

Где вы можете терять контакт {moon_basis}:
{loss}

Почему это может происходить {moon_basis}:
{tension}

Ваш мягкий ключ {moon_basis}:
{key}

{bridge}{alternate_text}

Гармония здесь не в том, чтобы кто-то стал удобнее. Она в том, чтобы увидеть два разных входа в близость и найти между ними живой, тёплый проход.
""".strip()


def format_couple_full_report(man_report: PartnerReport, woman_report: PartnerReport) -> str:
    title, tension, bridge = _bridge_for(man_report.emotional_language, woman_report.emotional_language)
    strength, loss, key = _diagnostics_for(man_report.emotional_language, woman_report.emotional_language)
    precision_note = _pair_precision_note(man_report, woman_report)
    precision_block = f"\n\nТочность Луны:\n{precision_note}" if precision_note else ""
    moon_basis = _couple_basis(man_report, woman_report, "moon", "Луна")
    venus_basis = _couple_basis(man_report, woman_report, "venus", "Венера")
    mercury_basis = _couple_basis(man_report, woman_report, "mercury", "Меркурий")
    mars_basis = _couple_basis(man_report, woman_report, "mars", "Марс")
    alternate_block = _alternate_moon_bridge_block(man_report, woman_report)
    alternate_text = f"\n\n{alternate_block}" if alternate_block else ""
    return f"""
📖 Карта гармонии пары: {man_report.partner_name} + {woman_report.partner_name}

Эта карта не говорит, подходите вы друг другу или нет. Она показывает, какой эмоциональный ритм возникает между вами и где в нём можно найти больше тепла, ясности и доверия.

Ваш главный ритм {moon_basis}:
{title}{precision_block}

{_rhythm_for_man(man_report.emotional_language, _basis(man_report, "moon", "Луна"))}

{_rhythm_for_you(woman_report.emotional_language, _basis(woman_report, "moon", "Луна"))}

👤 Он подробнее
{_person_deep_profile(man_report, man_report.partner_name)}

👤 Она / вы подробнее
{_person_deep_profile(woman_report, woman_report.partner_name)}

Сильная сторона вашей пары {moon_basis}:
{strength}

Где вы можете терять контакт {moon_basis}:
{loss}

Почему это может происходить {moon_basis}:
{tension}

Ваш мягкий ключ {moon_basis}:
{key}

{bridge}{alternate_text}

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
