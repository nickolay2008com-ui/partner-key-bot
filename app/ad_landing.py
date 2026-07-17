from __future__ import annotations

import html
import json

from app import ad_attribution
from app.metrica_layer import _client_script, _counter_id

_INSTALLED = False


def build_landing_html(bot_link: str, attributed: bool) -> str:
    safe_link = html.escape(bot_link, quote=True)
    counter_id = _counter_id()
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Бесплатный первый ключ: что помогает мужчине чувствовать близость и какой шаг можно попробовать в общении с ним." />
  <title>Что помогает ему чувствовать близость</title>
  {_client_script(counter_id)}
  <style>
    :root {{ color-scheme:dark; --bg:#0e0b14; --card:#1d1827; --text:#fffaff; --muted:#c8bfd2; --accent:#a071ff; --accent-2:#8a5bea; --soft:#2a2434; --line:rgba(255,255,255,.11); }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; display:grid; place-items:center; padding:20px; background:radial-gradient(circle at 50% -10%,#563a72 0,#21182d 30%,var(--bg) 68%); color:var(--text); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(590px,100%); padding:clamp(24px,5vw,36px); border-radius:28px; background:rgba(29,24,39,.97); border:1px solid var(--line); box-shadow:0 28px 90px rgba(0,0,0,.38); }}
    .eyebrow {{ display:inline-flex; align-items:center; gap:7px; padding:7px 11px; border-radius:999px; background:var(--soft); color:#ded5e8; font-size:13px; }}
    h1 {{ margin:17px 0 12px; max-width:520px; font-size:clamp(31px,7.5vw,46px); line-height:1.05; letter-spacing:-.025em; }}
    .lead {{ margin:0 0 23px; color:var(--muted); font-size:clamp(16px,3vw,18px); line-height:1.52; }}
    .result {{ margin:0 0 20px; padding:18px; border-radius:20px; background:rgba(255,255,255,.055); border:1px solid rgba(255,255,255,.06); }}
    .result-title {{ margin:0 0 12px; color:#f5effb; font-size:14px; font-weight:800; text-transform:uppercase; letter-spacing:.055em; }}
    ul {{ display:grid; gap:12px; margin:0; padding:0; list-style:none; }}
    li {{ display:grid; grid-template-columns:22px 1fr; gap:8px; align-items:start; color:#f7f1fb; line-height:1.4; }}
    li::before {{ content:'✓'; color:#70e6a3; font-weight:900; }}
    .input-note {{ margin:0 0 16px; color:#e6ddec; text-align:center; font-size:14px; line-height:1.45; }}
    a.cta {{ display:block; padding:17px 20px; border-radius:17px; background:linear-gradient(135deg,var(--accent),var(--accent-2)); color:white; font-weight:850; text-align:center; text-decoration:none; font-size:17px; box-shadow:0 12px 28px rgba(139,92,246,.25); transition:transform .15s ease,filter .15s ease; }}
    a.cta:hover {{ filter:brightness(1.07); transform:translateY(-1px); }}
    a.cta:focus-visible {{ outline:3px solid rgba(255,255,255,.8); outline-offset:3px; }}
    .next-step {{ margin:11px 0 0; color:var(--muted); font-size:13px; line-height:1.45; text-align:center; }}
    .preview {{ margin:26px 0 0; padding-top:23px; border-top:1px solid var(--line); }}
    .preview-title {{ margin:0 0 13px; font-size:21px; letter-spacing:-.015em; }}
    .preview-card {{ padding:18px; border-radius:20px; background:linear-gradient(145deg,rgba(160,113,255,.13),rgba(255,255,255,.045)); border:1px solid rgba(160,113,255,.3); }}
    .preview-label {{ display:block; margin-bottom:10px; color:#cbb9f4; font-size:12px; font-weight:800; text-transform:uppercase; letter-spacing:.055em; }}
    .preview-card p {{ margin:0; color:#e8dfed; line-height:1.52; }}
    blockquote {{ margin:15px 0; padding:13px 14px; border-left:3px solid var(--accent); border-radius:0 13px 13px 0; background:rgba(0,0,0,.17); color:white; font-weight:700; line-height:1.45; }}
    .preview-note {{ margin:10px 0 17px; color:#aaa0b6; font-size:12px; line-height:1.45; }}
    .cta-secondary {{ background:transparent!important; border:1px solid rgba(160,113,255,.75); box-shadow:none!important; }}
    .trust {{ margin:18px 0 0; color:#aaa0b6; font-size:12px; line-height:1.5; text-align:center; }}
    @media (max-width:480px) {{
      body {{ padding:12px; place-items:start center; }}
      main {{ margin-top:8px; border-radius:24px; }}
      .result {{ padding:16px; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">💞 Астро Партнёр · первый ключ бесплатно</div>
    <h1>Поймите, что помогает ему чувствовать близость</h1>
    <p class="lead">По дате рождения мужчины бот покажет, как он чаще воспринимает заботу, от чего может закрываться и какой мягкий шаг стоит проверить в общении с ним.</p>
    <section class="result" aria-labelledby="result-title">
      <p class="result-title" id="result-title">За 2 минуты вы получите</p>
      <ul>
        <li>какой формат заботы ему может быть понятнее;</li>
        <li>что иногда заставляет его защищаться или отдаляться;</li>
        <li>какую фразу или действие можно попробовать сегодня.</li>
      </ul>
    </section>
    <p class="input-note">Нужны только имя и дата рождения. Точное время необязательно.</p>
    <a class="cta" id="open-bot" data-open-bot href="{safe_link}">Получить бесплатный ключ в Telegram</a>
    <p class="next-step">Откроется бот — нажмите «Запустить», и он начнёт разбор.</p>
    <section class="preview" aria-labelledby="preview-title">
      <h2 class="preview-title" id="preview-title">Как выглядит подсказка</h2>
      <div class="preview-card">
        <span class="preview-label">Пример одного из вариантов</span>
        <p>Ему легче открываться через разговор, ясность, юмор и ощущение пространства. Намёки и молчаливые обиды могут заставлять его дистанцироваться.</p>
        <blockquote>«Хочу спокойно понять тебя, а не спорить. Как ты сам видишь нашу ситуацию?»</blockquote>
        <p><strong>На что смотреть:</strong> он начинает объяснять, задаёт встречный вопрос или предлагает продолжить разговор.</p>
      </div>
      <p class="preview-note">Это пример. Ваш результат будет рассчитан по его дате рождения.</p>
      <a class="cta cta-secondary" data-open-bot href="{safe_link}">Получить свой бесплатный ключ</a>
    </section>
    <p class="trust">Без оценки совместимости и обещаний изменить человека. Вы получите гипотезу, которую можно сравнить с его реальными реакциями.</p>
  </main>
  <script>
    const target = {json.dumps(bot_link)};
    const metricaId = {json.dumps(counter_id)};
    document.querySelectorAll('[data-open-bot]').forEach((button) => {{
      button.addEventListener('click', (event) => {{
        event.preventDefault();
        let redirected = false;
        const openTelegram = () => {{
          if (redirected) return;
          redirected = true;
          window.location.href = target;
        }};
        const metricEvent = {{
          event: 'landing_to_bot',
          payload: {{ attributed: {str(attributed).lower()} }},
          at: new Date().toISOString()
        }};
        window.partnerKeyEvents = window.partnerKeyEvents || [];
        window.partnerKeyEvents.push(metricEvent);
        try {{
          if (metricaId && typeof window.ym === 'function') {{
            window.ym(metricaId, 'reachGoal', 'landing_to_bot', metricEvent.payload, openTelegram);
            window.setTimeout(openTelegram, 1200);
            return;
          }}
        }} catch (_error) {{}}
        openTelegram();
      }});
    }});
  </script>
</body>
</html>"""


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ad_attribution.build_landing_html = build_landing_html
    _INSTALLED = True
