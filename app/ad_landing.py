from __future__ import annotations

import html
import json
from urllib.parse import urlencode

from app import ad_attribution
from app.metrica_layer import _client_script, _counter_id

_INSTALLED = False


def build_landing_html(bot_link: str, attributed: bool, token: str = "") -> str:
    click_link = f"/go/out?{urlencode({'token': token})}" if attributed and token else bot_link
    safe_link = html.escape(click_link, quote=True)
    counter_id = _counter_id()
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Бесплатная персональная подсказка: как мужчина воспринимает заботу, почему закрывается и какую фразу попробовать без давления." />
  <title>Как найти подход к вашему мужчине</title>
  {_client_script(counter_id)}
  <style>
    :root {{ --ink:#241b2b; --muted:#6f6375; --plum:#6936a8; --plum-dark:#522582; --lilac:#f2eafa; --rose:#fff5f4; --card:#fffdfd; --line:#e9dfe9; --green:#23805a; }}
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
<body>
  <main>
    <section class="hero" aria-labelledby="page-title">
      <div class="eyebrow">💞 Астро Партнёр · первый разбор бесплатно</div>
      <h1 id="page-title">Как он чувствует заботу — и почему иногда закрывается</h1>
      <p class="lead">По имени и дате рождения мужчины вы получите персональную подсказку: что помогает ему идти на контакт и какую фразу попробовать без давления.</p>
      <div class="promise" aria-label="Что будет в результате">
        <div><strong>Его язык близости</strong>Какие слова и действия он легче принимает как заботу.</div>
        <div><strong>Причина дистанции</strong>Что может прозвучать для него как давление.</div>
        <div><strong>Проверяемый шаг</strong>Готовая фраза и реакция, на которую смотреть.</div>
      </div>
      <a class="cta" id="primary-cta" data-open-bot href="{safe_link}">Получить первый разбор бесплатно</a>
      <p class="micro">Откроется Telegram · около 2 минут · точное время рождения не нужно</p>
    </section>

    <section class="content" aria-labelledby="sample-title">
      <h2 id="sample-title">Вот как выглядит подсказка</h2>
      <div class="sample">
        <span class="sample-label">Пример одного из сценариев</span>
        <p>Ему легче открываться, когда разговор ясный, спокойный и оставляет пространство для ответа. Намёки и молчаливые проверки могут заставлять его дистанцироваться.</p>
        <blockquote>«Хочу спокойно понять тебя, а не спорить. Как ты сам видишь нашу ситуацию?»</blockquote>
        <p class="watch"><strong>На что смотреть:</strong> он начинает объяснять, задаёт встречный вопрос или предлагает продолжить разговор.</p>
      </div>
      <p class="micro">Это пример. Ваш результат будет рассчитан по его дате рождения.</p>
    </section>

    <section class="content" aria-labelledby="steps-title">
      <h2 id="steps-title">Всего три шага</h2>
      <ol class="steps">
        <li>Откройте Telegram и нажмите «Запустить».</li>
        <li>Напишите имя и дату рождения мужчины.</li>
        <li>Получите его эмоциональный ключ, готовую фразу и способ проверить подсказку.</li>
      </ol>
      <a class="cta" data-open-bot href="{safe_link}">Узнать, как найти к нему подход</a>
      <div class="free"><strong>Первый результат действительно бесплатный.</strong> Для него ничего покупать не нужно. Если захотите продолжить: подробный раздел — от 50 ₽, полная карта отношений — 199 ₽.</div>
      <p class="trust">Это не тест на совместимость и не предсказание судьбы. Вы получите ориентир, который можно сравнить с реальным поведением человека.</p>
    </section>
  </main>
  <a class="sticky" id="sticky-cta" data-open-bot href="{safe_link}">Получить бесплатный разбор</a>
  <script>
    const metricaId = {json.dumps(counter_id)};
    document.querySelectorAll('[data-open-bot]').forEach((button) => {{
      button.addEventListener('click', () => {{
        button.textContent = 'Открываем Telegram…';
        const payload = {{ attributed: {str(attributed).lower()}, version: 'cro_v2' }};
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
