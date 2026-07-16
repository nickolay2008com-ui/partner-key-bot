from __future__ import annotations

import html
import json

from app import ad_attribution
from app.metrica_layer import _client_script, _counter_id

_INSTALLED = False


def build_landing_html(bot_link: str, attributed: bool) -> str:
    attribution_note = (
        "Рекламный переход сохранён. После открытия Telegram нажмите «Запустить», чтобы бот получил рекламный код."
        if attributed
        else "Откройте бот и получите первый ключ. Рекламная атрибуция появится при переходе из объявления Яндекса."
    )
    safe_link = html.escape(bot_link, quote=True)
    counter_id = _counter_id()
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Инструкция к вашему мужчине</title>
  {_client_script(counter_id)}
  <style>
    :root {{ color-scheme: light dark; --bg:#0f0d16; --card:#1d1928; --text:#faf7ff; --muted:#c5bdd2; --accent:#9b6cff; --soft:#2a2338; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; min-height:100vh; padding:22px; background:radial-gradient(circle at top,#49325f 0,var(--bg) 52%); color:var(--text); font-family:system-ui,-apple-system,"Segoe UI",sans-serif; }}
    main {{ width:min(620px,100%); margin:0 auto; padding:28px; border-radius:28px; background:rgba(29,25,40,.96); border:1px solid rgba(255,255,255,.12); box-shadow:0 24px 70px rgba(0,0,0,.28); }}
    .eyebrow {{ display:inline-flex; padding:7px 11px; border-radius:999px; background:var(--soft); color:var(--muted); font-size:13px; }}
    h1 {{ margin:14px 0 10px; font-size:clamp(29px,7vw,42px); line-height:1.06; }}
    .lead {{ margin:0 0 22px; color:var(--muted); font-size:17px; line-height:1.5; }}
    ul {{ display:grid; gap:11px; margin:0 0 22px; padding:0; list-style:none; }}
    li {{ padding:13px 14px; border-radius:16px; background:rgba(255,255,255,.055); line-height:1.4; }}
    li::before {{ content:'✓'; margin-right:9px; color:#7ee2a8; font-weight:800; }}
    .price {{ margin:0 0 18px; padding:14px; border:1px solid rgba(155,108,255,.45); border-radius:16px; background:rgba(155,108,255,.10); line-height:1.45; }}
    a.cta {{ display:block; padding:16px 18px; border-radius:17px; background:var(--accent); color:white; font-weight:800; text-align:center; text-decoration:none; font-size:17px; }}
    .note {{ margin:14px 0 0; color:var(--muted); font-size:13px; line-height:1.45; text-align:center; }}
    .disclaimer {{ margin-top:22px; padding-top:18px; border-top:1px solid rgba(255,255,255,.1); color:var(--muted); font-size:13px; line-height:1.5; }}
  </style>
</head>
<body>
  <main>
    <div class="eyebrow">💞 Астро Партнёр · Telegram-бот</div>
    <h1>Инструкция к вашему мужчине</h1>
    <p class="lead">По дате рождения бот покажет, что помогает ему чувствовать близость, как он слышит заботу и какой мягкий шаг можно попробовать в реальной жизни.</p>
    <ul>
      <li>Первый эмоциональный ключ бесплатно</li>
      <li>Эмоциональный мост вашей пары после добавления своей даты</li>
      <li>Практичная фраза или действие без давления и гадания по молчанию</li>
    </ul>
    <p class="price"><strong>Первый ключ бесплатно.</strong><br />Подробные разделы — от 50 ₽, полная карта отношений — 199 ₽.</p>
    <a class="cta" id="open-bot" href="{safe_link}">Открыть Telegram и нажать «Запустить»</a>
    <p class="note">{html.escape(attribution_note)}</p>
    <p class="disclaimer">Это не медицинская или психологическая диагностика и не обещание результата. Бот помогает посмотреть на привычный ритм пары и выбрать проверяемый шаг.</p>
  </main>
  <script>
    const target = {json.dumps(bot_link)};
    const metricaId = {json.dumps(counter_id)};
    document.getElementById('open-bot').addEventListener('click', (event) => {{
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
  </script>
</body>
</html>"""


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ad_attribution.build_landing_html = build_landing_html
    _INSTALLED = True
