from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlparse

from app.astro.calculator import calculate_partner_chart, parse_birth_date
from app.astro.product_blocks import (
    format_couple_full_report,
    format_couple_moon_bridge,
    format_couple_portraits,
    format_moon_variant_cards,
    format_jupiter_detail,
    format_mars_detail,
    format_mercury_detail,
    format_moon_detail,
    format_venus_detail,
)
from app.astro.report import PartnerReport, build_partner_report
from app.config import settings
from app.storage import ReportsStore

logger = logging.getLogger(__name__)
_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path, settings.database_url)
    return _store


def _validate_init_data(init_data: str) -> int:
    if not init_data:
        raise ValueError("Откройте это окно из Telegram, чтобы бот понял, кто вы.")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", "")
    if not received_hash:
        raise ValueError("Telegram не передал подпись авторизации.")

    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(pairs.items()))
    secret_key = hmac.new(b"WebAppData", settings.telegram_bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("Не удалось подтвердить Telegram-пользователя.")

    raw_user = pairs.get("user")
    if not raw_user:
        raise ValueError("Telegram не передал пользователя.")
    user = json.loads(raw_user)
    user_id = int(user["id"])
    return user_id


WEBAPP_HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <script defer src="https://telegram.org/js/telegram-web-app.js"></script>
  <title>Мои данные</title>
  <style>
    :root {
      color-scheme: light dark;
      --bg: var(--tg-theme-bg-color, #101014);
      --card: var(--tg-theme-secondary-bg-color, #1b1b22);
      --text: var(--tg-theme-text-color, #f4f4f5);
      --hint: var(--tg-theme-hint-color, #9ca3af);
      --button: var(--tg-theme-button-color, #7c3aed);
      --button-text: var(--tg-theme-button-text-color, #ffffff);
      --border: rgba(255, 255, 255, 0.12);
      --success: #22c55e;
      --warm: #f59e0b;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 18px;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--text);
    }
    h1 { font-size: 26px; margin: 0 0 8px; line-height: 1.12; }
    p { margin: 0 0 18px; color: var(--hint); line-height: 1.45; }
    .hero {
      background: linear-gradient(135deg, rgba(124,58,237,0.22), rgba(245,158,11,0.12));
      border: 1px solid var(--border);
      border-radius: 24px;
      padding: 18px;
      margin-bottom: 14px;
    }
    .hero p { margin-bottom: 12px; }
    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 10px;
      border-radius: 999px;
      background: rgba(255,255,255,0.08);
      color: var(--hint);
      font-size: 13px;
      margin-bottom: 12px;
    }
    .bridge {
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 6px;
      margin-top: 12px;
    }
    .bridge-step {
      min-height: 58px;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 8px;
      background: rgba(255,255,255,0.05);
      font-size: 12px;
      line-height: 1.2;
    }
    .bridge-step strong { display: block; color: var(--text); margin-bottom: 3px; }
    .value-list { display: grid; gap: 8px; margin: 12px 0 0; padding: 0; list-style: none; }
    .value-list li { color: var(--hint); font-size: 14px; line-height: 1.35; }
    .value-list li::before { content: '✓'; color: var(--success); font-weight: 800; margin-right: 7px; }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 16px;
      margin-bottom: 14px;
    }
    .title { font-weight: 700; margin-bottom: 12px; }
    label { display: block; font-size: 14px; color: var(--hint); margin: 12px 0 6px; }
    input {
      width: 100%;
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 13px 14px;
      background: rgba(255,255,255,0.06);
      color: var(--text);
      font-size: 16px;
      outline: none;
    }
    input:focus { border-color: var(--button); }
    .row { display: grid; gap: 12px; }
    button {
      width: 100%;
      border: none;
      border-radius: 16px;
      padding: 14px 16px;
      font-size: 16px;
      font-weight: 700;
      background: var(--button);
      color: var(--button-text);
      margin-top: 8px;
    }
    .secondary {
      background: transparent;
      border: 1px solid var(--border);
      color: var(--text);
    }
    .status { min-height: 22px; margin-top: 12px; color: var(--hint); font-size: 14px; }
    .loading { opacity: .78; position: relative; overflow: hidden; }
    .loading::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%); background: linear-gradient(90deg, transparent, rgba(255,255,255,.12), transparent); animation: shimmer 1.15s infinite; }
    @keyframes shimmer { 100% { transform: translateX(100%); } }
    .hint-box {
      border: 1px dashed var(--border);
      border-radius: 16px;
      padding: 12px;
      margin-bottom: 14px;
      color: var(--hint);
      font-size: 14px;
      line-height: 1.4;
    }
    .cta-note { margin: 8px 2px 0; font-size: 13px; color: var(--hint); text-align: center; }
    @media (max-width: 360px) {
      .bridge { grid-template-columns: repeat(2, 1fr); }
    }
  </style>
</head>
<body>
  <section class="hero" aria-labelledby="page-title">
    <div class="eyebrow">💞 Мини-профиль для разбора пары</div>
    <h1 id="page-title">Сохраните даты — получите эмоциональный мост без повторного ввода</h1>
    <p>Бот сопоставит ваш ритм и ритм партнёра: где возникает сомнение, что помогает понять друг друга, чему можно доверять и какой первый шаг сделать мягче.</p>
    <div class="bridge" aria-label="Эмоциональный путь пользователя">
      <div class="bridge-step"><strong>Сомнение</strong>«Почему он так реагирует?»</div>
      <div class="bridge-step"><strong>Понимание</strong>что ему спокойнее</div>
      <div class="bridge-step"><strong>Доверие</strong>без давления и угадывания</div>
      <div class="bridge-step"><strong>Действие</strong>готовая мягкая фраза</div>
    </div>
    <ul class="value-list">
      <li>Данные нужны только чтобы не вводить их заново в каждом разборе.</li>
      <li>После сохранения можно быстрее открыть мост пары и варианты сообщения.</li>
    </ul>
  </section>

  <div class="hint-box">Заполните минимум имя и дату партнёра. Добавьте свою дату, если хотите сразу видеть общий эмоциональный мост, а не только его портрет.</div>

  <div class="card">
    <div class="title">Ваши данные</div>
    <label for="self_name">Имя</label>
    <input id="self_name" autocomplete="name" placeholder="Например: Анна" />
    <label for="self_birth_date">Дата рождения</label>
    <input id="self_birth_date" inputmode="numeric" autocomplete="bday" maxlength="10" placeholder="12.04.1993" />
  </div>

  <div class="card">
    <div class="title">Партнёр</div>
    <label for="partner_name">Имя партнёра</label>
    <input id="partner_name" placeholder="Например: Андрей" />
    <label for="partner_birth_date">Дата рождения партнёра</label>
    <input id="partner_birth_date" inputmode="numeric" maxlength="10" placeholder="06.11.1995" />
  </div>

  <button id="save">Сохранить и вернуться к разбору</button>
  <div class="cta-note">Следующий шаг — нажать в боте «Показать наш эмоциональный мост» или «Что написать?».</div>
  <button id="close" class="secondary">Закрыть без изменений</button>
  <div class="status" id="status">Открываю форму…</div>

  <script>
    let tg;
    document.body.classList.add('loading');
    const statusEl = document.getElementById('status');
    const fields = ['self_name', 'self_birth_date', 'partner_name', 'partner_birth_date'];
    const dateFields = ['self_birth_date', 'partner_birth_date'];

    function status(text) { statusEl.textContent = text || ''; }
    function stopLoading() { document.body.classList.remove('loading'); }
    function track(eventName, payload = {}) {
      const event = { event: eventName, payload, at: new Date().toISOString() };
      window.partnerKeyEvents = window.partnerKeyEvents || [];
      window.partnerKeyEvents.push(event);
      if (window.console && console.debug) console.debug('partner_key_event', event);
    }
    function formatBirthDateInput(value) {
      const digits = String(value || '').replace(/\D/g, '').slice(0, 8);
      const parts = [digits.slice(0, 2), digits.slice(2, 4), digits.slice(4, 8)].filter(Boolean);
      return parts.join('.');
    }
    function isCompleteBirthDate(value) {
      return /^\d{2}\.\d{2}\.\d{4}$/.test(value);
    }
    function applyBirthDateMask(input) {
      input.value = formatBirthDateInput(input.value);
    }
    function validateBirthDateMasks(profile) {
      for (const id of dateFields) {
        if (profile[id] && !isCompleteBirthDate(profile[id])) {
          throw new Error('Введите дату полностью по маске ДД.ММ.ГГГГ, например 12.04.1993.');
        }
      }
    }
    function profileFromForm() {
      const result = {};
      for (const id of fields) result[id] = document.getElementById(id).value.trim();
      for (const id of dateFields) result[id] = formatBirthDateInput(result[id]);
      validateBirthDateMasks(result);
      return result;
    }
    function fillForm(profile) {
      for (const id of fields) document.getElementById(id).value = profile[id] || '';
      for (const id of dateFields) applyBirthDateMask(document.getElementById(id));
    }
    async function api(action, profile) {
      const response = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, profile, initData: tg ? tg.initData : '' })
      });
      const data = await response.json();
      if (!response.ok || !data.ok) throw new Error(data.error || 'Ошибка запроса');
      return data;
    }

    async function load() {
      if (!tg || !tg.initData) {
        status('Откройте это окно из Telegram, иначе идентификация не сработает. Да, безопасность решила вмешаться.');
        stopLoading();
        return;
      }
      tg.ready();
      tg.expand();
      track('profile_webapp_opened');
      status('Загружаю данные…');
      try {
        const data = await api('get');
        fillForm(data.profile || {});
        const profile = data.profile || {};
        track('profile_loaded', {
          hasSelfDate: Boolean(profile.self_birth_date),
          hasPartnerDate: Boolean(profile.partner_birth_date)
        });
        status('Данные загружены. Можно обновить их и вернуться к разбору.');
        stopLoading();
      } catch (error) {
        status(error.message);
        stopLoading();
      }
    }

    document.getElementById('save').addEventListener('click', async () => {
      status('Сохраняю…');
      try {
        const profile = profileFromForm();
        track('profile_save_clicked', {
          hasSelfDate: Boolean(profile.self_birth_date),
          hasPartnerDate: Boolean(profile.partner_birth_date)
        });
        const data = await api('save', profile);
        fillForm(data.profile || {});
        track('profile_saved', {
          hasSelfDate: Boolean((data.profile || {}).self_birth_date),
          hasPartnerDate: Boolean((data.profile || {}).partner_birth_date)
        });
        status('Сохранено. Вернитесь в бот — теперь эмоциональный мост и тексты можно собрать быстрее.');
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      } catch (error) {
        status(error.message);
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
      }
    });
    document.getElementById('close').addEventListener('click', () => {
      track('profile_webapp_closed');
      if (tg) tg.close();
    });
    for (const id of dateFields) {
      const input = document.getElementById(id);
      input.addEventListener('input', () => applyBirthDateMask(input));
      input.addEventListener('blur', () => applyBirthDateMask(input));
      input.addEventListener('paste', () => setTimeout(() => applyBirthDateMask(input), 0));
    }

    document.addEventListener('DOMContentLoaded', () => {
      tg = window.Telegram && window.Telegram.WebApp;
      load();
    });
  </script>
</body>
</html>
"""


DETAIL_LABELS = {
    "moon": "🌙 Луна: где ему спокойно",
    "venus": "💗 Венера: что включает тепло",
    "mercury": "🗣 Меркурий: как договориться",
    "mars": "🔥 Марс: как поддержать действие",
    "jupiter": "🪐 Юпитер: куда расти вместе",
    "portrait": "👤 Портреты в отношениях",
    "full": "📖 Карта гармонии пары",
    "bridge": "💞 Эмоциональный мост",
}


def _report_from_payload(payload: dict[str, Any] | None) -> PartnerReport | None:
    if not isinstance(payload, dict):
        return None
    payload = {key: value for key, value in payload.items() if key != "_storage_report_id"}
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


def _detail_text(user_id: int, block: str) -> str:
    store = get_store()
    man_report = _report_from_payload(store.latest_report_payload(user_id))
    if man_report is None:
        raise ValueError("Сначала соберите разбор в боте — тогда здесь откроется подробная карта.")
    if block in {"portrait", "full", "bridge"}:
        profile = store.get_profile(user_id)
        self_birth_date = profile.get("self_birth_date", "")
        if not self_birth_date:
            raise ValueError("Для карты пары добавьте вашу дату рождения в мини-профиле.")
        woman_chart = calculate_partner_chart(parse_birth_date(self_birth_date))
        woman_report = build_partner_report(woman_chart, profile.get("self_name") or "вы")
        if block == "full":
            return format_couple_full_report(man_report, woman_report)
        if block == "bridge":
            return format_couple_moon_bridge(man_report, woman_report)
        return format_couple_portraits(man_report, woman_report)
    formatters = {
        "moon": format_moon_detail,
        "venus": format_venus_detail,
        "mercury": format_mercury_detail,
        "mars": format_mars_detail,
        "jupiter": format_jupiter_detail,
    }
    formatter = formatters.get(block)
    if formatter is None:
        raise ValueError("Этот подробный блок пока не найден.")
    return formatter(man_report)


DETAIL_WEBAPP_HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
  <script defer src="https://telegram.org/js/telegram-web-app.js"></script>
  <title>Подробный разбор</title>
  <style>
    :root { color-scheme: light dark; --bg: var(--tg-theme-bg-color, #100f17); --text: var(--tg-theme-text-color, #f8fafc); --hint: var(--tg-theme-hint-color, #b6adc8); --button: var(--tg-theme-button-color, #8b5cf6); --border: rgba(255,255,255,.13); --glow: rgba(236,72,153,.24); }
    * { box-sizing: border-box; }
    body { margin: 0; padding: 18px; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at top, var(--glow), transparent 34%), var(--bg); color: var(--text); }
    .hero, .content { border: 1px solid var(--border); border-radius: 24px; background: rgba(255,255,255,.055); box-shadow: 0 18px 50px rgba(0,0,0,.18); }
    .hero { padding: 18px; margin-bottom: 14px; }
    .eyebrow { display: inline-flex; padding: 7px 11px; border-radius: 999px; background: rgba(255,255,255,.09); color: var(--hint); font-size: 13px; margin-bottom: 12px; }
    h1 { font-size: 25px; line-height: 1.12; margin: 0 0 8px; }
    p { margin: 0; color: var(--hint); line-height: 1.45; }
    .content { padding: 18px; font-size: 16px; line-height: 1.55; white-space: pre-wrap; }
    .skeleton { color: var(--hint); }
    .skeleton-line { display: block; height: 14px; margin: 12px 0; border-radius: 999px; background: linear-gradient(90deg, rgba(255,255,255,.07), rgba(255,255,255,.16), rgba(255,255,255,.07)); background-size: 220% 100%; animation: shimmer 1.1s infinite linear; }
    .skeleton-line:nth-child(2) { width: 88%; }
    .skeleton-line:nth-child(3) { width: 72%; }
    @keyframes shimmer { to { background-position: -220% 0; } }
    .life-use { display: none; margin: 0 0 14px; padding: 16px; border: 1px solid var(--border); border-radius: 22px; background: rgba(255,255,255,.07); }
    .life-use.is-visible { display: block; }
    .life-use h2 { margin: 0 0 10px; font-size: 20px; line-height: 1.18; }
    .use-grid { display: grid; gap: 10px; }
    .use-card { border: 1px solid var(--border); border-radius: 16px; padding: 12px; background: rgba(0,0,0,.13); }
    .use-card strong { display: block; margin-bottom: 5px; }
    .use-card span { color: var(--hint); line-height: 1.4; }
    .variant-wrap { display: none; margin: 0 0 14px; }
    .variant-wrap.is-visible { display: block; }
    .variant-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 8px; color: var(--hint); font-size: 14px; }
    .variant-carousel { display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; padding-bottom: 8px; }
    .variant-card { flex: 0 0 88%; scroll-snap-align: start; border: 1px solid var(--border); border-radius: 20px; padding: 14px; background: rgba(255,255,255,.075); white-space: pre-wrap; line-height: 1.48; }
    .variant-card h2 { margin: 0 0 8px; font-size: 18px; line-height: 1.2; }
    .variant-card p { color: var(--text); white-space: pre-wrap; }
    .close { width: 100%; margin-top: 14px; border: 0; border-radius: 16px; padding: 14px; background: var(--button); color: var(--tg-theme-button-text-color, #fff); font-weight: 800; font-size: 16px; }
  </style>
</head>
<body>
  <section class="hero">
    <div class="eyebrow">✨ Подробный разбор карты</div>
    <h1 id="title">Загружаю…</h1>
    <p>Смотрите не как приговор, а как практичную подсказку: что попробовать в словах, внимании и ежедневном контакте.</p>
  </section>
  <section class="life-use" id="life-use" aria-labelledby="life-use-title">
    <h2 id="life-use-title">Как применять карту в жизни</h2>
    <div class="use-grid">
      <div class="use-card"><strong>Понимание партнёра</strong><span>Смотрите, что стоит за реакцией: потребность в спокойствии, тепле, ясных словах или поддержке действия.</span></div>
      <div class="use-card"><strong>Гармонизация отношений</strong><span>Выберите один маленький мост на сегодня вместо большого разговора обо всём: вопрос, просьбу, паузу или ритуал контакта.</span></div>
      <div class="use-card"><strong>Практика без давления</strong><span>Проверяйте подсказки мягко: если партнёр закрывается, снижайте темп и возвращайтесь к безопасности диалога.</span></div>
    </div>
  </section>
  <section class="variant-wrap" id="variants" aria-labelledby="variants-title">
    <div class="variant-head"><strong id="variants-title">Свайп вариантов Луны</strong><span>выберите, что больше похоже на жизнь</span></div>
    <div class="variant-carousel" id="variant-carousel"></div>
  </section>
  <main class="content skeleton" id="content" aria-busy="true">
    Открываю подробности…
    <span class="skeleton-line"></span>
    <span class="skeleton-line"></span>
    <span class="skeleton-line"></span>
  </main>
  <button class="close" id="close">Вернуться в Telegram</button>
  <script>
    let tg;
    const params = new URLSearchParams(location.search);
    const block = params.get('block') || 'moon';
    function renderVariants(variants) {
      if (!variants.length) return;
      const wrap = document.getElementById('variants');
      const carousel = document.getElementById('variant-carousel');
      carousel.innerHTML = '';
      variants.forEach((item, index) => {
        const card = document.createElement('article');
        card.className = 'variant-card';
        const title = document.createElement('h2');
        title.textContent = `${index + 1}. ${item.title || 'Вариант Луны'}`;
        const text = document.createElement('p');
        text.textContent = item.text || '';
        card.append(title, text);
        carousel.append(card);
      });
      wrap.classList.add('is-visible');
    }
    async function load() {
      try {
        const response = await fetch('/api/detail', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ block, initData: tg ? tg.initData : '' })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Не удалось открыть подробности.');
        document.getElementById('title').textContent = data.title;
        if (block === 'full' || block === 'bridge') document.getElementById('life-use').classList.add('is-visible');
        renderVariants(data.variants || []);
        const content = document.getElementById('content');
        content.classList.remove('skeleton');
        content.removeAttribute('aria-busy');
        content.textContent = data.text;
      } catch (error) {
        document.getElementById('title').textContent = 'Нужен Telegram';
        const content = document.getElementById('content');
        content.classList.remove('skeleton');
        content.removeAttribute('aria-busy');
        content.textContent = error.message;
      }
    }
    document.getElementById('close').addEventListener('click', () => tg ? tg.close() : history.back());
    document.addEventListener('DOMContentLoaded', () => {
      tg = window.Telegram && window.Telegram.WebApp;
      if (tg) { tg.ready(); tg.expand(); }
      load();
    });
  </script>
</body>
</html>"""


class WebAppHandler(BaseHTTPRequestHandler):
    server_version = "PartnerKeyWebApp/1.0"

    def log_message(self, format: str, *args: Any) -> None:
        logger.info("WEBAPP: " + format, *args)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_html(self, html: str) -> None:
        body = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        return json.loads(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/healthz":
            try:
                storage = get_store().healthcheck()
                self._send_json({"ok": bool(storage.get("ok")), "storage": storage})
            except Exception as exc:
                logger.exception("HEALTHCHECK_STORAGE_FAILED")
                self._send_json({"ok": False, "error": str(exc)}, status=503)
            return
        if path == "/webapp":
            self._send_html(WEBAPP_HTML)
            return
        if path == "/webapp/detail":
            self._send_html(DETAIL_WEBAPP_HTML)
            return
        self._send_json({"ok": False, "error": "not_found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/detail":
            try:
                payload = self._read_json()
                user_id = _validate_init_data(str(payload.get("initData", "")))
                block = str(payload.get("block", "moon"))
                text = _detail_text(user_id, block)
                variants = []
                if block in {"bridge", "full"}:
                    profile = get_store().get_profile(user_id)
                    man_report = _report_from_payload(get_store().latest_report_payload(user_id))
                    if man_report is not None and profile.get("self_birth_date"):
                        woman_chart = calculate_partner_chart(parse_birth_date(profile.get("self_birth_date", "")))
                        woman_report = build_partner_report(woman_chart, profile.get("self_name") or "вы")
                        if "changed_during_day" in {man_report.moon_status, woman_report.moon_status}:
                            variants = format_moon_variant_cards(man_report, woman_report)
                get_store().track_event(user_id, "detail_webapp_opened", {"block": block})
                self._send_json(
                    {
                        "ok": True,
                        "title": DETAIL_LABELS.get(block, "✨ Подробный разбор"),
                        "text": text,
                        "variants": variants,
                    }
                )
            except Exception as exc:
                logger.exception("DETAIL_WEBAPP_FAILED")
                self._send_json({"ok": False, "error": str(exc)}, status=400)
            return
        if path != "/api/profile":
            self._send_json({"ok": False, "error": "not_found"}, status=404)
            return
        try:
            payload = self._read_json()
            user_id = _validate_init_data(str(payload.get("initData", "")))
            action = str(payload.get("action", "get"))
            store = get_store()
            if action == "save":
                profile = store.save_profile(
                    user_id,
                    payload.get("profile") if isinstance(payload.get("profile"), dict) else {},
                )
            else:
                profile = store.get_profile(user_id)
            self._send_json({"ok": True, "profile": profile})
        except Exception as exc:
            logger.warning("WEBAPP_PROFILE_ERROR: %s", exc)
            self._send_json({"ok": False, "error": str(exc)}, status=400)


def start_webapp_server() -> ThreadingHTTPServer:
    port = int(os.getenv("PORT", "8080"))
    server = ThreadingHTTPServer(("0.0.0.0", port), WebAppHandler)
    thread = threading.Thread(target=server.serve_forever, name="telegram-webapp-server", daemon=True)
    thread.start()
    logger.info("WEBAPP_SERVER: started on port %s", port)
    return server
