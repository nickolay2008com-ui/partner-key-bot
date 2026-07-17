from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qsl, urlparse

from app.astro.calculator import calculate_partner_chart, parse_birth_date
from app.astro.emotional_bridge import build_couple_moon_bridge_view
from app.astro.product_blocks import (
    format_couple_full_report,
    format_couple_moon_bridge,
    format_couple_portraits,
    format_moon_variant_cards,
    format_jupiter_detail,
    format_mars_detail,
    format_mercury_detail,
    format_moon_deep_detail,
    format_moon_detail,
    format_venus_detail,
)
from app.astro.relationship_map import build_couple_full_map_view
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

    try:
        auth_date = int(pairs.get("auth_date", "0"))
    except (TypeError, ValueError):
        auth_date = 0
    if auth_date <= 0 or abs(int(time.time()) - auth_date) > 86400:
        raise ValueError("Авторизация Telegram устарела. Закройте окно и откройте его из бота ещё раз.")

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
      <div class="bridge-step"><strong>Доверие</strong>через ясность и бережность</div>
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

DETAIL_BLOCKS = {
    "moon",
    "moon_deep",
    "venus",
    "mercury",
    "mars",
    "jupiter",
    "portrait",
    "full",
    "bridge",
    "details",
}


def _normalize_detail_block(block: str | None) -> str:
    candidate = str(block or "moon").strip().lower().replace("-", "_")
    if candidate not in DETAIL_BLOCKS:
        raise ValueError("Этот подробный блок пока не найден.")
    return candidate


DETAIL_LABELS = {
    "moon": "🌙 Луна: как стать его тихой гаванью",
    "moon_deep": "🌙 Луна мужчины глубже",
    "venus": "💗 Венера: как включить его нежность",
    "mercury": "🗣 Меркурий: слова, которые он слышит",
    "mars": "🔥 Марс: как дать ему силу действовать",
    "jupiter": "🪐 Юпитер: куда вести вашу пару",
    "portrait": "👤 Портреты в отношениях",
    "full": "📖 Карта гармонии пары",
    "bridge": "💞 Эмоциональный мост",
    "details": "🔍 Глубже о его эмоциональном ритме",
}


def _report_from_payload(payload: dict[str, Any] | None) -> PartnerReport | None:
    if not isinstance(payload, dict):
        return None
    payload = {key: value for key, value in payload.items() if key != "_storage_report_id"}
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


def _detail_text(user_id: int, block: str, report_id: int = 0) -> str:
    store = get_store()
    payload = store.report_payload(user_id, report_id) if report_id > 0 else store.latest_report_payload(user_id)
    man_report = _report_from_payload(payload)
    if man_report is None:
        raise ValueError("Сначала соберите разбор в боте — тогда здесь откроется подробная карта.")
    if block == "details":
        return man_report.text
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
            return format_couple_moon_bridge(man_report, woman_report, include_transition_variants=False)
        return format_couple_portraits(man_report, woman_report)
    formatters = {
        "moon": format_moon_detail,
        "moon_deep": format_moon_deep_detail,
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
    body { max-width: 760px; margin: 0 auto; padding: 18px; font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: radial-gradient(circle at top, var(--glow), transparent 34%), var(--bg); color: var(--text); }
    .hero, .content { border: 1px solid var(--border); border-radius: 24px; background: rgba(255,255,255,.055); box-shadow: 0 18px 50px rgba(0,0,0,.18); }
    .hero { padding: 18px; margin-bottom: 14px; }
    .eyebrow { display: inline-flex; padding: 7px 11px; border-radius: 999px; background: rgba(255,255,255,.09); color: var(--hint); font-size: 12px; font-weight: 800; letter-spacing: .06em; text-transform: uppercase; margin-bottom: 12px; }
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
    .bridge-view { display: none; gap: 14px; }
    .bridge-view.is-visible { display: grid; }
    .bridge-formula { display: none; gap: 8px; margin-top: 16px; }
    .is-bridge .bridge-formula { display: grid; grid-template-columns: 1fr 1fr; }
    .formula-chip { padding: 11px 12px; border: 1px solid var(--border); border-radius: 15px; background: rgba(0,0,0,.14); }
    .formula-chip span, .formula-chip small { display: block; color: var(--hint); }
    .formula-chip span { margin-bottom: 3px; font-size: 12px; }
    .formula-chip strong { display: block; font-size: 14px; }
    .formula-chip small { margin-top: 3px; font-size: 12px; }
    .bridge-card { padding: 18px; border: 1px solid var(--border); border-radius: 24px; background: rgba(255,255,255,.06); box-shadow: 0 14px 38px rgba(0,0,0,.12); }
    .bridge-card.accent { background: linear-gradient(145deg, rgba(139,92,246,.24), rgba(236,72,153,.12)); }
    .bridge-kicker { margin-bottom: 8px; color: #d8b4fe; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; }
    .bridge-card h2 { margin: 0 0 10px; font-size: 22px; line-height: 1.18; }
    .bridge-card h3 { margin: 0 0 8px; font-size: 18px; line-height: 1.22; }
    .bridge-card p { color: var(--text); }
    .bridge-accent { margin-top: 14px; padding: 13px 14px; border-left: 3px solid #c084fc; border-radius: 4px 14px 14px 4px; background: rgba(0,0,0,.16); font-weight: 700; line-height: 1.45; }
    .shore-grid { display: grid; gap: 10px; }
    .shore-card { padding: 15px; border: 1px solid var(--border); border-radius: 19px; background: rgba(0,0,0,.13); }
    .shore-head { display: flex; justify-content: space-between; gap: 10px; align-items: start; margin-bottom: 12px; }
    .shore-role { color: #d8b4fe; font-size: 12px; font-weight: 900; text-transform: uppercase; letter-spacing: .06em; }
    .shore-sign { color: var(--hint); font-size: 13px; text-align: right; }
    .shore-line { margin-top: 11px; }
    .shore-line strong { display: block; margin-bottom: 3px; font-size: 13px; }
    .shore-line span { color: var(--hint); line-height: 1.42; }
    .protocol-list { display: grid; gap: 10px; margin-top: 12px; }
    .protocol-step { display: grid; grid-template-columns: 42px 1fr; gap: 11px; align-items: start; padding: 13px; border: 1px solid var(--border); border-radius: 17px; background: rgba(0,0,0,.13); }
    .protocol-step b { color: #d8b4fe; font-size: 13px; letter-spacing: .06em; }
    .protocol-step strong { display: block; margin-bottom: 4px; }
    .protocol-step span { color: var(--hint); line-height: 1.42; }
    .phrase-tabs { display: flex; gap: 8px; overflow-x: auto; margin: 12px 0; padding-bottom: 2px; }
    .phrase-tab { flex: 0 0 auto; border: 1px solid var(--border); border-radius: 999px; padding: 9px 12px; background: rgba(0,0,0,.13); color: var(--hint); font-weight: 800; }
    .phrase-tab.is-active { border-color: transparent; background: var(--button); color: var(--tg-theme-button-text-color, #fff); }
    .phrase-box { min-height: 142px; padding: 16px; border: 1px solid var(--border); border-radius: 18px; background: rgba(0,0,0,.16); }
    .phrase-box strong { display: block; margin-bottom: 8px; }
    .phrase-box p { font-size: 17px; line-height: 1.52; }
    .copy-phrase { width: 100%; margin-top: 12px; border: 1px solid var(--border); border-radius: 14px; padding: 11px; background: rgba(255,255,255,.08); color: var(--text); font-weight: 800; }
    .check-list { display: grid; gap: 9px; margin: 12px 0 0; padding: 0; list-style: none; }
    .check-list li { position: relative; padding-left: 28px; color: var(--hint); line-height: 1.43; }
    .check-list li::before { content: '✓'; position: absolute; left: 0; top: -1px; display: grid; place-items: center; width: 20px; height: 20px; border-radius: 999px; background: rgba(74,222,128,.17); color: #86efac; font-weight: 900; }
    .boundary { margin-top: 15px; padding: 13px; border: 1px solid rgba(251,191,36,.24); border-radius: 15px; background: rgba(251,191,36,.08); color: var(--hint); line-height: 1.43; }
    .bridge-note { color: var(--hint) !important; font-size: 14px; }
    .is-bridge .content { display: none; }
    @media (min-width: 620px) { .shore-grid { grid-template-columns: 1fr 1fr; } }
    .full-map-view { display: none; gap: 14px; }
    .full-map-view.is-visible { display: grid; }
    .is-full-map .content, .is-full-map .life-use { display: none; }
    .map-summary-grid { display: grid; gap: 9px; margin-top: 12px; }
    .map-summary-card { padding: 13px; border: 1px solid var(--border); border-radius: 17px; background: rgba(0,0,0,.13); }
    .map-summary-card small { display: block; margin-bottom: 5px; color: #d8b4fe; font-weight: 900; letter-spacing: .05em; text-transform: uppercase; }
    .map-summary-card strong { display: block; margin-bottom: 5px; }
    .map-summary-card p { color: var(--hint); font-size: 14px; }
    .layer-stack { display: grid; gap: 10px; margin-top: 12px; }
    .planet-layer { overflow: hidden; border: 1px solid var(--border); border-radius: 20px; background: rgba(0,0,0,.13); }
    .planet-layer summary { display: grid; grid-template-columns: 40px 1fr 22px; gap: 10px; align-items: center; padding: 14px; cursor: pointer; list-style: none; }
    .planet-layer summary::-webkit-details-marker { display: none; }
    .planet-icon { display: grid; place-items: center; width: 38px; height: 38px; border-radius: 13px; background: rgba(139,92,246,.18); font-size: 20px; }
    .planet-heading strong, .planet-heading span, .planet-heading small { display: block; }
    .planet-heading span { margin-top: 3px; color: var(--hint); font-size: 13px; }
    .planet-heading small { margin-top: 6px; color: #c4b5fd; font-size: 11px; line-height: 1.35; }
    .planet-chevron { color: var(--hint); font-size: 18px; transition: transform .2s ease; }
    .planet-layer[open] .planet-chevron { transform: rotate(180deg); }
    .planet-body { display: grid; gap: 12px; padding: 0 14px 14px; }
    .pair-insight { padding: 13px; border-radius: 16px; background: rgba(255,255,255,.055); }
    .pair-insight strong { display: block; margin-bottom: 5px; }
    .pair-insight p { color: var(--hint); }
    .map-side-grid { display: grid; gap: 9px; }
    .map-side { padding: 13px; border: 1px solid var(--border); border-radius: 16px; background: rgba(255,255,255,.045); }
    .map-side-head { display: flex; justify-content: space-between; gap: 10px; margin-bottom: 9px; }
    .map-side-head strong { color: #d8b4fe; }
    .map-side-head span { color: var(--hint); font-size: 12px; text-align: right; }
    .map-side dl { display: grid; gap: 8px; margin: 0; }
    .map-side dt { margin-bottom: 2px; font-size: 12px; font-weight: 900; }
    .map-side dd { margin: 0; color: var(--hint); line-height: 1.4; }
    .exact-note { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--border); color: var(--hint); font-size: 13px; line-height: 1.4; }
    .layer-action { padding: 14px; border-radius: 17px; background: linear-gradient(145deg, rgba(139,92,246,.18), rgba(236,72,153,.08)); }
    .layer-action strong { display: block; margin-bottom: 5px; }
    .layer-action p { color: var(--text); }
    .layer-action .phrase { margin-top: 11px; padding: 12px; border-left: 3px solid #c084fc; border-radius: 4px 13px 13px 4px; background: rgba(0,0,0,.17); }
    .layer-action .result { margin-top: 11px; color: var(--hint); font-size: 14px; }
    .copy-layer { width: 100%; margin-top: 10px; border: 1px solid var(--border); border-radius: 13px; padding: 10px; background: rgba(255,255,255,.08); color: var(--text); font-weight: 800; }
    .week-grid { display: grid; gap: 9px; margin-top: 12px; }
    .week-day { display: grid; grid-template-columns: 62px 1fr; gap: 10px; padding: 12px; border: 1px solid var(--border); border-radius: 16px; background: rgba(0,0,0,.13); }
    .week-day b { color: #d8b4fe; font-size: 12px; }
    .week-day strong { display: block; margin-bottom: 3px; }
    .week-day span { color: var(--hint); line-height: 1.4; }
    @media (min-width: 620px) {
      .map-summary-grid { grid-template-columns: repeat(3, 1fr); }
      .map-side-grid { grid-template-columns: 1fr 1fr; }
      .week-grid { grid-template-columns: 1fr 1fr; }
    }
    .variant-wrap { display: none; margin: 0 0 14px; }
    .variant-wrap.is-visible { display: block; }
    .variant-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 8px; color: var(--hint); font-size: 14px; }
    .variant-carousel { display: flex; gap: 12px; overflow-x: auto; scroll-snap-type: x mandatory; -webkit-overflow-scrolling: touch; padding-bottom: 8px; }
    .variant-card { flex: 0 0 88%; scroll-snap-align: start; border: 1px solid var(--border); border-radius: 20px; padding: 14px; background: rgba(255,255,255,.075); white-space: pre-wrap; line-height: 1.48; }
    .variant-card h2 { margin: 0 0 8px; font-size: 18px; line-height: 1.2; }
    .variant-card p { color: var(--text); white-space: pre-wrap; }
    .toast { position: fixed; left: 50%; bottom: 78px; z-index: 5; transform: translate(-50%, 16px); padding: 10px 14px; border-radius: 999px; background: #111827; color: #fff; opacity: 0; pointer-events: none; transition: .2s ease; font-size: 14px; font-weight: 800; }
    .toast.is-visible { opacity: 1; transform: translate(-50%, 0); }
    .close { width: 100%; margin-top: 14px; border: 0; border-radius: 16px; padding: 14px; background: var(--button); color: var(--tg-theme-button-text-color, #fff); font-weight: 800; font-size: 16px; }
  </style>
</head>
<body>
  <section class="hero">
    <div class="eyebrow" id="eyebrow">✨ Инструкция к любимому мужчине</div>
    <h1 id="title">Загружаю…</h1>
    <p id="hero-copy">Это не сухой прогноз, а мягкая инструкция: какие слова, внимание и действия помогают ему раскрыться рядом с вами.</p>
    <div class="bridge-formula" id="bridge-formula"></div>
  </section>
  <section class="life-use" id="life-use" aria-labelledby="life-use-title">
    <h2 id="life-use-title">Как применять карту в жизни</h2>
    <div class="use-grid">
      <div class="use-card"><strong>Понимание партнёра</strong><span>Смотрите, что стоит за реакцией: потребность в спокойствии, тепле, ясных словах или поддержке действия.</span></div>
      <div class="use-card"><strong>Гармонизация отношений</strong><span>Выберите один маленький мост на сегодня вместо большого разговора обо всём: вопрос, просьбу, паузу или ритуал контакта.</span></div>
      <div class="use-card"><strong>Бережная практика</strong><span>Проверяйте подсказки мягко: если партнёр закрывается, снижайте темп и возвращайтесь к безопасности диалога.</span></div>
    </div>
  </section>
  <main class="bridge-view" id="bridge-view" aria-live="polite"></main>
  <main class="full-map-view" id="full-map-view" aria-live="polite"></main>
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
  <div class="toast" id="toast" role="status">Фраза скопирована</div>
  <button class="close" id="close">Вернуться в Telegram</button>
  <script>
    let tg;
    const params = new URLSearchParams(location.search);
    const pathBlock = decodeURIComponent(location.pathname.split('/').filter(Boolean).pop() || '');
    const block = params.get('block') || (pathBlock === 'detail' ? 'moon' : pathBlock) || 'moon';
    const reportId = Number(params.get('report_id') || 0);
    const cacheKey = reportId > 0 ? `partner-key-detail:${reportId}:${block}:v12` : '';
    function setBusy(isBusy) {
      const content = document.getElementById('content');
      if (isBusy) {
        content.classList.add('skeleton');
        content.setAttribute('aria-busy', 'true');
      } else {
        content.classList.remove('skeleton');
        content.removeAttribute('aria-busy');
      }
    }
    function el(tag, className = '', text = '') {
      const item = document.createElement(tag);
      if (className) item.className = className;
      if (text) item.textContent = text;
      return item;
    }
    function bridgeCard(kicker, title, className = '') {
      const card = el('section', `bridge-card ${className}`.trim());
      if (kicker) card.append(el('div', 'bridge-kicker', kicker));
      if (title) card.append(el('h2', '', title));
      return card;
    }
    function renderFormula(items) {
      const formula = document.getElementById('bridge-formula');
      formula.replaceChildren();
      (items || []).forEach(item => {
        const chip = el('div', 'formula-chip');
        chip.append(el('span', '', item.label || ''));
        chip.append(el('strong', '', item.value || ''));
        chip.append(el('small', '', item.element || ''));
        formula.append(chip);
      });
    }
    function renderShore(item) {
      const card = el('article', 'shore-card');
      const head = el('div', 'shore-head');
      const identity = el('div');
      identity.append(el('div', 'shore-role', item.role || 'Берег'));
      identity.append(el('h3', '', item.name || ''));
      head.append(identity, el('div', 'shore-sign', `${item.sign || ''} · ${item.element || ''}`));
      card.append(head, el('p', 'bridge-note', item.tagline || ''));
      [
        ['Что создаёт безопасность', item.need],
        ['Что может закрывать', item.closes],
        ['Как строить мост', item.bridge],
        ['Сильный вклад в пару', item.gift]
      ].forEach(([label, text]) => {
        const line = el('div', 'shore-line');
        line.append(el('strong', '', label), el('span', '', text || ''));
        card.append(line);
      });
      return card;
    }
    function renderChecklist(items) {
      const list = el('ul', 'check-list');
      (items || []).forEach(item => list.append(el('li', '', item)));
      return list;
    }
    async function copyPhrase(text) {
      try {
        await navigator.clipboard.writeText(text);
      } catch (_error) {
        const field = el('textarea');
        field.value = text;
        field.style.position = 'fixed';
        field.style.opacity = '0';
        document.body.append(field);
        field.select();
        document.execCommand('copy');
        field.remove();
      }
      const toast = document.getElementById('toast');
      toast.classList.add('is-visible');
      if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('success');
      setTimeout(() => toast.classList.remove('is-visible'), 1600);
    }
    function renderPhrases(phrases) {
      const card = bridgeCard('Слова, которые не предают вас', 'Выберите фразу под ситуацию');
      const tabs = el('div', 'phrase-tabs');
      const box = el('div', 'phrase-box');
      const phraseTitle = el('strong');
      const phraseText = el('p');
      const copy = el('button', 'copy-phrase', 'Скопировать фразу');
      copy.type = 'button';
      const select = index => {
        const item = phrases[index];
        phraseTitle.textContent = item.title || '';
        phraseText.textContent = `«${item.text || ''}»`;
        copy.onclick = () => copyPhrase(item.text || '');
        [...tabs.children].forEach((tab, tabIndex) => tab.classList.toggle('is-active', tabIndex === index));
      };
      phrases.forEach((item, index) => {
        const tab = el('button', 'phrase-tab', item.label || `Вариант ${index + 1}`);
        tab.type = 'button';
        tab.onclick = () => select(index);
        tabs.append(tab);
      });
      box.append(phraseTitle, phraseText, copy);
      card.append(tabs, box);
      if (phrases.length) select(0);
      return card;
    }
    function renderBridge(model) {
      document.body.classList.add('is-bridge');
      document.getElementById('eyebrow').textContent = model.eyebrow || 'Лунный код пары';
      document.getElementById('title').textContent = model.title || 'Ваш эмоциональный мост';
      document.getElementById('hero-copy').textContent = model.subtitle || '';
      document.getElementById('close').textContent = 'Вернуться в Telegram';
      renderFormula(model.formula || []);
      const view = document.getElementById('bridge-view');
      view.replaceChildren();

      const insight = bridgeCard(model.insight.kicker, model.insight.title, 'accent');
      insight.append(el('p', '', model.insight.body));
      insight.append(el('div', 'bridge-accent', model.insight.accent));
      view.append(insight);

      const shores = bridgeCard('Два берега одной связи', 'Что каждый из вас называет близостью');
      const shoreGrid = el('div', 'shore-grid');
      (model.shores || []).forEach(item => shoreGrid.append(renderShore(item)));
      shores.append(shoreGrid);
      view.append(shores);

      const translation = bridgeCard(model.translation.kicker, model.translation.title);
      translation.append(el('p', '', model.translation.body));
      translation.append(el('div', 'bridge-accent', model.translation.rule));
      view.append(translation);

      const protocol = bridgeCard('Маршрут контакта', 'Ваш мост в трёх шагах');
      const protocolList = el('div', 'protocol-list');
      (model.protocol || []).forEach(item => {
        const step = el('div', 'protocol-step');
        const copy = el('div');
        copy.append(el('strong', '', item.title), el('span', '', item.text));
        step.append(el('b', '', item.number), copy);
        protocolList.append(step);
      });
      protocol.append(protocolList);
      view.append(protocol);

      view.append(renderPhrases(model.phrases || []));

      const experiment = bridgeCard(model.experiment.kicker, model.experiment.title, 'accent');
      experiment.append(renderChecklist(model.experiment.steps));
      experiment.append(el('h3', '', 'Как понять, что мост работает'));
      experiment.append(renderChecklist(model.experiment.success));
      experiment.append(el('div', 'boundary', model.experiment.boundary));
      view.append(experiment);

      const astrology = bridgeCard('Астрологическая оптика', model.astrology.title);
      astrology.append(el('p', 'bridge-note', model.astrology.body));
      if (model.astrology.precision) astrology.append(el('div', 'boundary', model.astrology.precision));
      view.append(astrology);

      const next = bridgeCard(model.next_level.kicker, model.next_level.title);
      next.append(el('p', 'bridge-note', model.next_level.body));
      view.append(next);
      view.classList.add('is-visible');
    }
    function renderMapSide(item) {
      const card = el('article', 'map-side');
      const head = el('div', 'map-side-head');
      head.append(
        el('strong', '', `${item.role || ''}: ${item.name || ''}`),
        el('span', '', `${item.sign || ''} · ${item.element || ''}${item.motion ? ` · ${item.motion}` : ''}`)
      );
      const list = el('dl');
      [
        ['Что нужно', item.need],
        ['Сильный вклад', item.gift],
        ['Слепая зона', item.risk || item.closes]
      ].forEach(([label, text]) => {
        const row = el('div');
        row.append(el('dt', '', label), el('dd', '', text || ''));
        list.append(row);
      });
      card.append(head, list);
      if (item.exact) card.append(el('div', 'exact-note', item.exact));
      return card;
    }
    function renderPlanetLayer(layer, index) {
      const details = el('details', 'planet-layer');
      details.open = index === 0;
      const summary = el('summary');
      const heading = el('div', 'planet-heading');
      heading.append(el('strong', '', layer.title), el('span', '', layer.promise), el('small', '', layer.formula));
      summary.append(el('div', 'planet-icon', layer.emoji), heading, el('div', 'planet-chevron', '⌄'));

      const body = el('div', 'planet-body');
      const resource = el('div', 'pair-insight');
      resource.append(el('strong', '', 'Что уже работает на вас'), el('p', '', layer.resource));
      const friction = el('div', 'pair-insight');
      friction.append(el('strong', '', 'Где нужен перевод'), el('p', '', layer.friction));
      const sides = el('div', 'map-side-grid');
      (layer.sides || []).forEach(item => sides.append(renderMapSide(item)));

      const action = el('div', 'layer-action');
      action.append(el('strong', '', 'Один практический шаг'), el('p', '', layer.action));
      const phrase = el('div', 'phrase');
      phrase.append(el('strong', '', 'Фраза-мост'), el('p', '', `«${layer.phrase}»`));
      const copy = el('button', 'copy-layer', 'Скопировать фразу');
      copy.type = 'button';
      copy.onclick = () => copyPhrase(layer.phrase || '');
      action.append(phrase, copy, el('div', 'result', `Признак результата: ${layer.success}`));
      body.append(resource, friction, sides, action);
      details.append(summary, body);
      return details;
    }
    function renderFullMap(model) {
      document.body.classList.add('is-full-map');
      document.getElementById('eyebrow').textContent = model.eyebrow || 'Полная карта отношений';
      document.getElementById('title').textContent = model.title || 'Стратегия вашей пары';
      document.getElementById('hero-copy').textContent = model.subtitle || '';
      document.getElementById('close').textContent = 'Вернуться в Telegram';
      const view = document.getElementById('full-map-view');
      view.replaceChildren();

      const vector = bridgeCard(model.vector.kicker, model.vector.title, 'accent');
      vector.append(el('p', '', model.vector.body));
      const summary = el('div', 'map-summary-grid');
      (model.summary || []).forEach(item => {
        const card = el('article', 'map-summary-card');
        card.append(el('small', '', item.label), el('strong', '', item.title), el('p', '', item.text));
        summary.append(card);
      });
      vector.append(summary);
      view.append(vector);

      const layers = bridgeCard('Пять уровней отношений', 'Откройте слой, который важен вам сейчас');
      const stack = el('div', 'layer-stack');
      (model.layers || []).forEach((layer, index) => stack.append(renderPlanetLayer(layer, index)));
      layers.append(stack);
      view.append(layers);

      const week = bridgeCard('Из понимания в опыт', 'План пары на семь дней', 'accent');
      const weekGrid = el('div', 'week-grid');
      (model.week_plan || []).forEach(item => {
        const day = el('div', 'week-day');
        const copy = el('div');
        copy.append(el('strong', '', item.title), el('span', '', item.text));
        day.append(el('b', '', item.day), copy);
        weekGrid.append(day);
      });
      week.append(weekGrid);
      view.append(week);

      const method = bridgeCard('Точность и границы', model.method.title);
      method.append(el('p', 'bridge-note', model.method.body));
      if (model.method.precision) method.append(el('div', 'boundary', model.method.precision));
      view.append(method);
      view.classList.add('is-visible');
    }
    function applyDetail(data, fromCache = false) {
      document.getElementById('title').textContent = data.title || '✨ Подробный разбор';
      renderVariants(data.variants || []);
      const content = document.getElementById('content');
      setBusy(false);
      if (block === 'bridge' && data.bridge) renderBridge(data.bridge);
      else if (block === 'full' && data.fullMap) renderFullMap(data.fullMap);
      else content.textContent = data.text || '';
      if (fromCache) content.dataset.fromCache = 'true';
    }
    function renderCachedDetail() {
      try {
        if (!cacheKey) return false;
        const cached = JSON.parse(sessionStorage.getItem(cacheKey) || 'null');
        if (cached && cached.text) {
          applyDetail(cached, true);
          return true;
        }
      } catch (_error) {}
      return false;
    }
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
      const hasCache = renderCachedDetail();
      try {
        const response = await fetch('/api/detail', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ block, reportId, initData: tg ? tg.initData : '' })
        });
        const data = await response.json();
        if (!response.ok || !data.ok) throw new Error(data.error || 'Не удалось открыть подробности.');
        applyDetail(data);
        try {
          if (cacheKey) sessionStorage.setItem(cacheKey, JSON.stringify(data));
        } catch (_error) {}
      } catch (error) {
        if (hasCache) return;
        document.getElementById('title').textContent = 'Нужен Telegram';
        setBusy(false);
        document.getElementById('content').textContent = error.message;
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
        self.send_header("Cache-Control", "no-store")
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
        if path == "/webapp/detail" or path.startswith("/webapp/detail/"):
            try:
                if path.startswith("/webapp/detail/"):
                    _normalize_detail_block(path.rsplit("/", 1)[-1])
                self._send_html(DETAIL_WEBAPP_HTML)
            except ValueError as exc:
                self._send_json({"ok": False, "error": str(exc)}, status=404)
            return
        self._send_json({"ok": False, "error": "not_found"}, status=404)

    def do_POST(self) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path == "/api/detail":
            try:
                payload = self._read_json()
                user_id = _validate_init_data(str(payload.get("initData", "")))
                block = _normalize_detail_block(str(payload.get("block", "moon")))
                try:
                    report_id = int(payload.get("reportId", 0) or 0)
                except (TypeError, ValueError):
                    report_id = 0
                if report_id > 0 and get_store().report_payload(user_id, report_id) is None:
                    raise ValueError("Этот разбор не принадлежит текущему Telegram-пользователю.")
                text = _detail_text(user_id, block, report_id)
                variants = []
                bridge_view = None
                full_map_view = None
                if block in {"bridge", "full"}:
                    profile = get_store().get_profile(user_id)
                    report_payload = (
                        get_store().report_payload(user_id, report_id)
                        if report_id > 0
                        else get_store().latest_report_payload(user_id)
                    )
                    man_report = _report_from_payload(report_payload)
                    if man_report is not None and profile.get("self_birth_date"):
                        woman_chart = calculate_partner_chart(parse_birth_date(profile.get("self_birth_date", "")))
                        woman_report = build_partner_report(woman_chart, profile.get("self_name") or "вы")
                        if block == "bridge":
                            bridge_view = build_couple_moon_bridge_view(man_report, woman_report)
                        if block == "full":
                            full_map_view = build_couple_full_map_view(man_report, woman_report)
                        if "changed_during_day" in {man_report.moon_status, woman_report.moon_status}:
                            variants = format_moon_variant_cards(man_report, woman_report)
                get_store().track_event(
                    user_id,
                    "detail_webapp_opened",
                    {"block": block, "report_id": report_id},
                )
                self._send_json(
                    {
                        "ok": True,
                        "title": DETAIL_LABELS.get(block, "✨ Подробный разбор"),
                        "text": text,
                        "bridge": bridge_view,
                        "fullMap": full_map_view,
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
