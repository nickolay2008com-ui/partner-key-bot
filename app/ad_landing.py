from __future__ import annotations

import html
import json
from dataclasses import dataclass
from urllib.parse import urlencode

from app import ad_attribution
from app.metrica_layer import _client_script, _counter_id

_INSTALLED = False


@dataclass(frozen=True)
class LandingCopy:
    title: str
    description: str
    eyebrow: str
    headline: str
    lead: str
    benefits: tuple[tuple[str, str], tuple[str, str], tuple[str, str]]
    primary_cta: str
    sample_label: str
    sample_text: str
    sample_quote: str
    sample_watch: str
    secondary_cta: str
    trust: str


_LANDINGS = {
    "relationship": LandingCopy(
        title="Как найти подход к вашему мужчине",
        description="Бесплатная персональная подсказка: как мужчина воспринимает заботу, почему закрывается и какую фразу попробовать без давления.",
        eyebrow="💞 Астро Партнёр · первый разбор бесплатно",
        headline="Как он чувствует заботу — и почему иногда закрывается",
        lead="По имени и дате рождения мужчины вы получите персональную подсказку: что помогает ему идти на контакт и какую фразу попробовать без давления.",
        benefits=(
            ("Его язык близости", "Какие слова и действия он легче принимает как заботу."),
            ("Причина дистанции", "Что может прозвучать для него как давление."),
            ("Проверяемый шаг", "Готовая фраза и реакция, на которую смотреть."),
        ),
        primary_cta="Получить первый разбор бесплатно",
        sample_label="Пример одного из сценариев",
        sample_text="Ему легче открываться, когда разговор ясный, спокойный и оставляет пространство для ответа. Намёки и молчаливые проверки могут заставлять его дистанцироваться.",
        sample_quote="«Хочу спокойно понять тебя, а не спорить. Как ты сам видишь нашу ситуацию?»",
        sample_watch="он начинает объяснять, задаёт встречный вопрос или предлагает продолжить разговор.",
        secondary_cta="Узнать, как найти к нему подход",
        trust="Это не тест на совместимость и не предсказание судьбы. Вы получите ориентир, который можно сравнить с реальным поведением человека.",
    ),
    "money": LandingCopy(
        title="Как спокойно говорить с ним о деньгах",
        description="Первый бесплатный ключ подскажет, как начать разговор о деньгах без давления и не усилить защитную реакцию мужчины.",
        eyebrow="💳 Деньги в паре · первый ключ бесплатно",
        headline="Почему разговор о деньгах с ним быстро становится напряжённым?",
        lead="По дате рождения мужчины вы узнаете, что помогает ему оставаться в контакте, какой тон включает защиту и как начать сложный разговор спокойнее.",
        benefits=(
            ("Понять реакцию", "Что ему важнее: ясность, свобода или эмоциональная безопасность."),
            ("Не усилить защиту", "Какие слова и интонации могут восприниматься как давление."),
            ("Начать с фразы", "Первый шаг к разговору о расходах, планах или общих решениях."),
        ),
        primary_cta="Получить его эмоциональный ключ бесплатно",
        sample_label="Пример применения к теме денег",
        sample_text="Если он слышит в вопросе контроль или обвинение, то может защищаться ещё до обсуждения цифр. Начните с общей задачи и одного конкретного вопроса.",
        sample_quote="«Мне важно не спорить, кто прав, а понять, как нам обоим удобнее обращаться с деньгами. Обсудим сначала наши общие расходы?»",
        sample_watch="он остаётся в разговоре, называет свои приоритеты или предлагает свой вариант договорённости.",
        secondary_cta="Начать разговор о деньгах спокойнее",
        trust="Это не финансовый прогноз и не расчёт денежной совместимости. Бот помогает найти эмоциональные условия для спокойного разговора, а не борьбы.",
    ),
    "message": LandingCopy(
        title="Что написать ему без давления",
        description="Бесплатная персональная подсказка и фраза, которая поможет начать разговор бережнее и проверить реакцию мужчины.",
        eyebrow="💬 Персональная подсказка для разговора",
        headline="Не знаете, что ему написать, чтобы не усилить дистанцию?",
        lead="По имени и дате рождения мужчины вы узнаете, что помогает ему идти на контакт, что заставляет закрываться и какую фразу проверить по его реакции.",
        benefits=(
            ("Фраза без давления", "Не общий шаблон, а вариант по его эмоциональному ритму."),
            ("Что не усиливать", "Напор, холод или неопределённость действуют на мужчин по-разному."),
            ("Признак ответа", "Смотрите, стал ли он объяснять, смягчился или сам продолжил контакт."),
        ),
        primary_cta="Получить бесплатную подсказку и фразу",
        sample_label="Пример одной из подсказок",
        sample_text="Когда человек отдаляется, длинное объяснение может восприниматься как дополнительное давление. Иногда лучше обозначить ценность контакта и оставить пространство для ответа.",
        sample_quote="«Мне важен наш контакт. Я хочу понять, что ты чувствуешь, и не хочу на тебя давить.»",
        sample_watch="он отвечает содержательно, объясняет своё состояние или сам предлагает продолжить разговор.",
        secondary_cta="Получить свою фразу бесплатно",
        trust="Фраза не управляет человеком и не гарантирует ответ. Она помогает начать разговор бережнее и проверить подсказку по реальной реакции.",
    ),
    "after_conflict": LandingCopy(
        title="Что написать мужчине после ссоры",
        description="Первый бесплатный ключ и бережная фраза для возобновления разговора после ссоры без новой волны обвинений.",
        eyebrow="🕊 После ссоры · первый ключ бесплатно",
        headline="Что написать мужчине после ссоры — без унижения и нового конфликта",
        lead="По дате рождения мужчины бот покажет, что обычно помогает ему выйти из защиты, какой первый шаг безопаснее и когда лучше не давить.",
        benefits=(
            ("Первое сообщение", "Короткая фраза вместо длинного выяснения отношений."),
            ("Что не ухудшать", "Какой тон может снова включить спор или молчание."),
            ("Признак готовности", "На какую реальную реакцию смотреть после сообщения."),
        ),
        primary_cta="Получить фразу после ссоры бесплатно",
        sample_label="Пример первого шага после конфликта",
        sample_text="Если мужчине важно сначала снизить напряжение, попытка немедленно разобрать все претензии может снова закрыть разговор. Обозначьте контакт и один понятный вопрос.",
        sample_quote="«Мне важен наш контакт. Не хочу продолжать спор — когда будем готовы, давай спокойно обсудим один момент?»",
        sample_watch="он называет время, отвечает по существу или сам делает шаг к спокойному разговору.",
        secondary_cta="Понять, как восстановить контакт",
        trust="Подсказка не гарантирует примирение и не оправдывает оскорбления или насилие. Она помогает выбрать бережный первый шаг там, где есть взаимное уважение.",
    ),
    "care": LandingCopy(
        title="Как мужчина воспринимает вашу заботу",
        description="Бесплатная подсказка покажет, какой формат заботы мужчина замечает, а какой может ошибочно услышать как давление.",
        eyebrow="🤍 Когда хорошие намерения не доходят",
        headline="Вы заботитесь о нём. А он точно считывает это как заботу?",
        lead="Первый эмоциональный ключ поможет понять, какие слова и действия ему легче принять, где поддержка превращается для него в давление и что проверить без самопожертвования.",
        benefits=(
            ("Его язык заботы", "Слова, действие, спокойствие или пространство считываются по-разному."),
            ("Точка закрытия", "Где помощь может прозвучать как контроль, допрос или требование."),
            ("Шаг без жертвы", "Один бережный способ проявиться и оценить встречную реакцию."),
        ),
        primary_cta="Узнать его язык заботы бесплатно",
        sample_label="Пример перевода заботы на его язык",
        sample_text="Если ему важны надёжность и конкретность, громкие признания могут работать слабее спокойного совместного плана.",
        sample_quote="«Хочу спокойно провести с тобой вечер. Давай без суеты поужинаем или прогуляемся?»",
        sample_watch="он принимает предложение, предлагает свой вариант или сам проявляет встречную заботу.",
        secondary_cta="Понять, как он принимает поддержку",
        trust="Это не инструкция, как заслужить любовь или стать удобнее. Подсказка имеет смысл только там, где есть встречное уважение и участие.",
    ),
    "mistake": LandingCopy(
        title="Как не испортить важный разговор",
        description="Персональная бесплатная подсказка: какой тон сохраняет контакт и с какой фразы начать сложный разговор с мужчиной.",
        eyebrow="⚠️ Перед важным разговором",
        headline="Одна привычная фраза может закрыть разговор ещё до его начала",
        lead="По дате рождения мужчины бот покажет, какой вход в сложную тему помогает ему оставаться в контакте и что может сразу включить защиту.",
        benefits=(
            ("Найти триггер", "Обвинение, неопределённость или напор действуют на мужчин по-разному."),
            ("Заменить фразу", "Сохранить свой смысл, но убрать формулировку, которая закрывает ответ."),
            ("Выбрать момент", "Понять, когда продолжать, а когда дать разговору паузу."),
        ),
        primary_cta="Проверить фразу перед разговором",
        sample_label="Пример более безопасного начала",
        sample_text="Если для него важна эмоциональная безопасность, разговор лучше начинать с цели контакта, а не с перечня прошлых ошибок.",
        sample_quote="«Мне важно обсудить это без обвинений. Когда мы сможем спокойно вернуться к одному вопросу?»",
        sample_watch="он не уходит в защиту, предлагает время или формулирует свою позицию.",
        secondary_cta="Получить фразу для сложного разговора",
        trust="Фраза не заставит мужчину согласиться и не заменит границы. Она лишь помогает не закрыть диалог первой же формулировкой.",
    ),
    "contribution": LandingCopy(
        title="Как договориться о вкладе в семью",
        description="Бесплатный эмоциональный ключ поможет начать разговор о деньгах, заботе и ответственности без спора о том, кто делает больше.",
        eyebrow="⚖️ Деньги, забота и ответственность",
        headline="Почему вы оба стараетесь, но каждому кажется, что он отдаёт больше?",
        lead="Вклад в семью измеряют не только деньгами. Бот поможет понять, что мужчина замечает как поддержку, где начинается защита и как перейти к конкретной договорённости.",
        benefits=(
            ("Что он считает вкладом", "Деньги, действия, время и эмоциональная поддержка имеют разный вес."),
            ("Невидимая нагрузка", "Как обозначить свой вклад без обесценивания его усилий."),
            ("Честная договорённость", "Один вопрос, который переводит спор в конкретные обязанности."),
        ),
        primary_cta="Узнать, какой вклад он замечает",
        sample_label="Пример разговора без подсчёта обид",
        sample_text="Когда каждый защищает собственный вклад, спор о справедливости быстро становится взаимным обвинением. Сначала уточните смысл поддержки, затем договоритесь о видимых действиях.",
        sample_quote="«Что для тебя сейчас означает поддержка в семье? Давай назовём по два конкретных дела, которые берём на себя.»",
        sample_watch="он признаёт часть вашей нагрузки, называет свою и соглашается на измеримый следующий шаг.",
        secondary_cta="Начать честный разговор о вкладе",
        trust="Бот не определяет, кто прав, и не оправдывает финансовое неравенство. Решения о деньгах и обязанностях принимает сама пара.",
    ),
    "growth": LandingCopy(
        title="Как поддержать рост мужчины и семьи",
        description="Первый бесплатный ключ поможет поговорить о заработке, развитии и общей цели без сравнения и удара по достоинству мужчины.",
        eyebrow="📈 Рост дохода и общий горизонт пары",
        headline="Как поддержать его стремление зарабатывать больше — и не задеть достоинство",
        lead="Совет о доходе легко услышать как «ты недостаточно успешен». Бот поможет подобрать форму поддержки, которая сохраняет контакт и ведёт к одному совместному шагу.",
        benefits=(
            ("Реакция на советы", "Когда мужчине нужен вопрос, признание усилий или конкретный план."),
            ("Поддержка без давления", "Как говорить о росте, не сравнивая его с другими."),
            ("Общая цель", "Перевести желание жить лучше в ближайшее совместное действие."),
        ),
        primary_cta="Узнать, какая поддержка помогает ему расти",
        sample_label="Пример разговора о росте семьи",
        sample_text="Если мужчина защищает самостоятельность, готовый совет может звучать как недоверие. Лучше признать усилие и предложить выбрать общую цель вместе.",
        sample_quote="«Я вижу, сколько ты вкладываешь. Давай выберем одну цель, которая улучшит жизнь семьи, и решим, чем я могу помочь без давления?»",
        sample_watch="он рассказывает о своих планах, выбирает цель или предлагает конкретный следующий шаг.",
        secondary_cta="Получить ключ для разговора о росте",
        trust="Это не денежный прогноз и не обещание увеличить доход. Бот помогает с эмоциональной стороной договорённости; финансовые решения требуют реальных цифр и действий.",
    ),
}


def build_landing_html(
    bot_link: str,
    attributed: bool,
    token: str = "",
    variant: str = "relationship",
) -> str:
    variant = variant if variant in _LANDINGS else "relationship"
    copy = _LANDINGS[variant]
    out_query = urlencode({"token": token, "variant": variant})
    click_link = f"/go/out?{out_query}" if attributed and token else bot_link
    safe_link = html.escape(click_link, quote=True)
    counter_id = _counter_id()
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="{copy.description}" />
  <title>{copy.title}</title>
  {_client_script(counter_id)}
  <style>
    :root {{ --ink:#241b2b; --muted:#6f6375; --plum:#6936a8; --plum-dark:#522582; --lilac:#f2eafa; --card:#fffdfd; --line:#e9dfe9; }}
    * {{ box-sizing:border-box; }}
    html {{ scroll-behavior:smooth; }}
    body {{ margin:0; background:linear-gradient(180deg,#fff7f6 0,#fbf7ff 45%,#fff 100%); color:var(--ink); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(680px,100%); margin:0 auto; padding:18px 18px 42px; }}
    .hero {{ position:relative; overflow:hidden; padding:clamp(25px,6vw,44px); border:1px solid var(--line); border-radius:30px; background:rgba(255,253,253,.96); box-shadow:0 22px 60px rgba(74,43,91,.11); }}
    .hero::after {{ content:""; position:absolute; width:250px; height:250px; right:-130px; top:-120px; border-radius:50%; background:radial-gradient(circle,rgba(162,105,214,.21),transparent 70%); pointer-events:none; }}
    .eyebrow {{ display:inline-flex; gap:7px; align-items:center; padding:7px 11px; border-radius:999px; background:var(--lilac); color:#623391; font-size:13px; font-weight:750; }}
    h1 {{ position:relative; margin:17px 0 13px; max-width:590px; font-size:clamp(32px,7.5vw,50px); line-height:1.02; letter-spacing:-.035em; }}
    .lead {{ margin:0 0 20px; color:var(--muted); font-size:clamp(17px,3.5vw,19px); line-height:1.5; }}
    .promise {{ display:grid; grid-template-columns:repeat(3,1fr); gap:9px; margin:0 0 20px; }}
    .promise div {{ padding:13px 12px; border-radius:15px; background:#faf6fc; color:#4d4052; font-size:13px; line-height:1.35; }}
    .promise strong {{ display:block; margin-bottom:3px; color:var(--ink); font-size:14px; }}
    a.cta {{ display:block; position:relative; z-index:1; padding:17px 20px; border-radius:17px; background:linear-gradient(135deg,#7842bc,var(--plum-dark)); color:white; font-size:17px; font-weight:850; line-height:1.25; text-align:center; text-decoration:none; box-shadow:0 12px 27px rgba(105,54,168,.24); transition:transform .15s ease,filter .15s ease; }}
    a.cta:hover {{ filter:brightness(1.05); transform:translateY(-1px); }}
    a.cta:focus-visible {{ outline:3px solid rgba(105,54,168,.3); outline-offset:3px; }}
    .micro {{ margin:10px 0 0; color:var(--muted); font-size:12.5px; line-height:1.45; text-align:center; }}
    section.content {{ margin:18px 0 0; padding:clamp(22px,5vw,32px); border:1px solid var(--line); border-radius:26px; background:var(--card); }}
    h2 {{ margin:0 0 15px; font-size:clamp(24px,5vw,31px); line-height:1.13; letter-spacing:-.025em; }}
    .sample {{ padding:19px; border:1px solid #e1d2ed; border-radius:20px; background:linear-gradient(145deg,#f8f1fc,#fffafa); }}
    .sample-label {{ display:block; margin-bottom:10px; color:#75439b; font-size:12px; font-weight:850; letter-spacing:.055em; text-transform:uppercase; }}
    .sample p {{ margin:0; color:#514455; line-height:1.53; }}
    blockquote {{ margin:15px 0; padding:13px 14px; border-left:4px solid #8651bb; border-radius:0 13px 13px 0; background:white; color:var(--ink); font-weight:750; line-height:1.45; }}
    .watch {{ padding-top:13px; border-top:1px solid #e8ddec; }}
    .steps {{ display:grid; gap:11px; margin:0 0 20px; padding:0; list-style:none; counter-reset:step; }}
    .steps li {{ display:grid; grid-template-columns:34px 1fr; gap:10px; align-items:center; color:#514655; line-height:1.42; counter-increment:step; }}
    .steps li::before {{ content:counter(step); display:grid; place-items:center; width:34px; height:34px; border-radius:50%; background:var(--lilac); color:#643394; font-weight:850; }}
    .free {{ margin:16px 0 0; padding:16px; border-radius:17px; background:#f4fbf7; color:#395d4d; font-size:14px; line-height:1.48; }}
    .free strong {{ color:#1f6548; }}
    .trust {{ margin:16px 2px 0; color:#827586; font-size:12px; line-height:1.5; text-align:center; }}
    .sticky {{ display:none; }}
    @media (max-width:560px) {{
      main {{ padding:10px 10px 90px; }}
      .hero {{ padding:24px 20px; border-radius:24px; }}
      h1 {{ font-size:34px; }}
      .lead {{ font-size:16px; line-height:1.44; }}
      .promise {{ grid-template-columns:1fr; gap:7px; }}
      .promise div {{ padding:10px 12px; }}
      section.content {{ padding:21px 18px; border-radius:22px; }}
      .sticky.visible {{ display:block; position:fixed; left:10px; right:10px; bottom:10px; z-index:10; padding:14px 16px; border-radius:15px; background:linear-gradient(135deg,#7842bc,var(--plum-dark)); color:white; font-weight:850; text-align:center; text-decoration:none; box-shadow:0 12px 35px rgba(51,24,68,.35); }}
    }}
  </style>
</head>
<body data-landing-variant="{variant}">
  <main>
    <section class="hero" aria-labelledby="page-title">
      <div class="eyebrow">{copy.eyebrow}</div>
      <h1 id="page-title">{copy.headline}</h1>
      <p class="lead">{copy.lead}</p>
      <div class="promise" aria-label="Что будет в результате">
        <div><strong>{copy.benefits[0][0]}</strong>{copy.benefits[0][1]}</div>
        <div><strong>{copy.benefits[1][0]}</strong>{copy.benefits[1][1]}</div>
        <div><strong>{copy.benefits[2][0]}</strong>{copy.benefits[2][1]}</div>
      </div>
      <a class="cta" id="primary-cta" data-open-bot href="{safe_link}">{copy.primary_cta}</a>
      <p class="micro">Откроется Telegram · около 2 минут · точное время рождения не нужно</p>
    </section>

    <section class="content" aria-labelledby="sample-title">
      <h2 id="sample-title">Вот как выглядит подсказка</h2>
      <div class="sample">
        <span class="sample-label">{copy.sample_label}</span>
        <p>{copy.sample_text}</p>
        <blockquote>{copy.sample_quote}</blockquote>
        <p class="watch"><strong>На что смотреть:</strong> {copy.sample_watch}</p>
      </div>
      <p class="micro">Это пример. Ваш результат будет рассчитан по его дате рождения.</p>
    </section>

    <section class="content" aria-labelledby="steps-title">
      <h2 id="steps-title">Всего три шага</h2>
      <ol class="steps">
        <li>Откройте Telegram и нажмите «Запустить».</li>
        <li>Напишите имя и дату рождения мужчины.</li>
        <li>Получите первый эмоциональный ключ, фразу и способ проверить подсказку.</li>
      </ol>
      <a class="cta" data-open-bot href="{safe_link}">{copy.secondary_cta}</a>
      <div class="free"><strong>Первый результат действительно бесплатный.</strong> Дополнительные тематические разделы — от 50 ₽, полная карта отношений — 199 ₽.</div>
      <p class="trust">{copy.trust}</p>
    </section>
  </main>
  <a class="sticky" id="sticky-cta" data-open-bot href="{safe_link}">{copy.primary_cta}</a>
  <script>
    const metricaId = {json.dumps(counter_id)};
    const landingVariant = {json.dumps(variant)};
    if (window.partnerMetricsTrack) window.partnerMetricsTrack('landing_viewed', {{ variant: landingVariant }});
    document.querySelectorAll('[data-open-bot]').forEach((button) => {{
      button.addEventListener('click', () => {{
        button.textContent = 'Открываем Telegram…';
        const payload = {{ attributed: {str(attributed).lower()}, variant: landingVariant, version: 'cro_v3' }};
        if (window.partnerMetricsTrack) window.partnerMetricsTrack('landing_to_bot', payload);
        else if (metricaId && typeof window.ym === 'function') {{
          try {{ window.ym(metricaId, 'reachGoal', 'landing_to_bot', payload); }} catch (_error) {{}}
        }}
      }});
    }});
    const primary = document.getElementById('primary-cta');
    const sticky = document.getElementById('sticky-cta');
    if ('IntersectionObserver' in window) {{
      new IntersectionObserver(([entry]) => sticky.classList.toggle('visible', !entry.isIntersecting), {{ threshold: 0.1 }}).observe(primary);
    }}
  </script>
</body>
</html>"""


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ad_attribution.build_landing_html = build_landing_html
    _INSTALLED = True
