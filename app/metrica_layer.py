from __future__ import annotations

import json
import logging
import os
import re
from typing import Any
from urllib.parse import urlparse

import app.webapp as webapp

logger = logging.getLogger(__name__)

_ALLOWED_EVENTS = {
    "profile_webapp_opened",
    "profile_loaded",
    "profile_load_failed",
    "profile_save_clicked",
    "profile_saved",
    "profile_save_failed",
    "profile_webapp_closed",
    "detail_webapp_opened",
    "detail_loaded",
    "detail_load_failed",
    "detail_webapp_closed",
}
_EVENT_RE = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_PARAM_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,39}$")
_INSTALLED = False

_PROFILE_TRACK_BLOCK = """    function track(eventName, payload = {}) {
      const event = { event: eventName, payload, at: new Date().toISOString() };
      window.partnerKeyEvents = window.partnerKeyEvents || [];
      window.partnerKeyEvents.push(event);
      if (window.console && console.debug) console.debug('partner_key_event', event);
    }
"""

_PROFILE_TRACK_REPLACEMENT = """    function track(eventName, payload = {}) {
      if (window.partnerMetricsTrack) window.partnerMetricsTrack(eventName, payload);
    }
"""

_CLIENT_SCRIPT_TEMPLATE = r"""
<script id="partner-yandex-metrica">
  (() => {
    const METRICA_ID = __COUNTER_ID__;
    __METRICA_INIT__

    function sendGoal(name, payload) {
      if (!METRICA_ID || typeof window.ym !== 'function') return;
      try { window.ym(METRICA_ID, 'reachGoal', name, payload || {}); } catch (_error) {}
    }

    function sendInternal(name, payload) {
      try {
        const tg = window.Telegram && window.Telegram.WebApp;
        const initData = tg && tg.initData ? tg.initData : '';
        if (!initData) return;
        const body = JSON.stringify({ initData, event: name, payload: payload || {} });
        if (navigator.sendBeacon) {
          navigator.sendBeacon('/api/analytics', new Blob([body], { type: 'application/json' }));
          return;
        }
        fetch('/api/analytics', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body,
          keepalive: true
        }).catch(() => {});
      } catch (_error) {}
    }

    window.partnerMetricsTrack = function partnerMetricsTrack(eventName, payload = {}) {
      const name = String(eventName || '').trim();
      if (!/^[a-z][a-z0-9_]{1,63}$/.test(name)) return;
      const params = payload && typeof payload === 'object' ? payload : {};
      const event = { event: name, payload: params, at: new Date().toISOString() };
      window.partnerKeyEvents = window.partnerKeyEvents || [];
      window.partnerKeyEvents.push(event);
      if (window.console && console.debug) console.debug('partner_key_event', event);

      sendGoal(name, params);
      if (name === 'detail_webapp_opened') {
        if (params.block === 'bridge') sendGoal('bridge_opened', params);
        else if (params.block === 'full') sendGoal('full_map_opened', params);
        else if (['moon', 'moon_deep', 'venus', 'mercury', 'mars', 'jupiter'].includes(params.block)) {
          sendGoal('planet_opened', params);
        }
      }
      sendInternal(name, params);
    };
  })();
</script>
""".strip()


def _counter_id() -> int | None:
    raw = os.getenv("YANDEX_METRICA_ID", "").strip()
    if not raw:
        return None
    try:
        value = int(raw)
    except ValueError:
        logger.warning("YANDEX_METRICA_ID must be an integer; analytics tag is disabled")
        return None
    return value if value > 0 else None


def _client_script(counter_id: int | None = None) -> str:
    actual_id = counter_id if counter_id is not None else _counter_id()
    if actual_id:
        init = f"""
    (function(m,e,t,r,i,k,a){{m[i]=m[i]||function(){{(m[i].a=m[i].a||[]).push(arguments)}};
    m[i].l=1*new Date();k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)}})
    (window, document, 'script', 'https://mc.yandex.ru/metrika/tag.js', 'ym');
    window.ym({actual_id}, 'init', {{
      clickmap: true,
      trackLinks: true,
      accurateTrackBounce: true,
      webvisor: false,
      sendTitle: false,
      params: {{ app: 'astro_partner', surface: 'telegram_webapp' }}
    }});
""".strip()
        counter_value = str(actual_id)
    else:
        init = ""
        counter_value = "null"
    return _CLIENT_SCRIPT_TEMPLATE.replace("__COUNTER_ID__", counter_value).replace("__METRICA_INIT__", init)


def _sanitize_payload(payload: object) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    result: dict[str, Any] = {}
    for raw_key, raw_value in list(payload.items())[:20]:
        key = str(raw_key)
        if not _PARAM_KEY_RE.fullmatch(key):
            continue
        if isinstance(raw_value, bool) or raw_value is None:
            result[key] = raw_value
        elif isinstance(raw_value, (int, float)):
            result[key] = raw_value
        elif isinstance(raw_value, str):
            result[key] = raw_value[:120]
    return result


def _patch_profile_html(html: str) -> str:
    patched = html.replace(_PROFILE_TRACK_BLOCK, _PROFILE_TRACK_REPLACEMENT, 1)
    patched = patched.replace(
        """      } catch (error) {
        status(error.message);
        stopLoading();
      }
    }

    document.getElementById('save')""",
        """      } catch (error) {
        track('profile_load_failed');
        status(error.message);
        stopLoading();
      }
    }

    document.getElementById('save')""",
        1,
    )
    patched = patched.replace(
        """      } catch (error) {
        status(error.message);
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
      }
    });""",
        """      } catch (error) {
        track('profile_save_failed');
        status(error.message);
        if (tg && tg.HapticFeedback) tg.HapticFeedback.notificationOccurred('error');
      }
    });""",
        1,
    )
    return patched


def _patch_detail_html(html: str) -> str:
    patched = html.replace(
        """    function setBusy(isBusy) {""",
        """    let detailMetricSent = false;
    function setBusy(isBusy) {""",
        1,
    )
    patched = patched.replace(
        """      if (fromCache) content.dataset.fromCache = 'true';
    }""",
        """      if (fromCache) content.dataset.fromCache = 'true';
      if (!detailMetricSent && window.partnerMetricsTrack) {
        detailMetricSent = true;
        window.partnerMetricsTrack('detail_loaded', { block, fromCache: Boolean(fromCache) });
      }
    }""",
        1,
    )
    patched = patched.replace(
        """      } catch (error) {
        if (hasCache) return;""",
        """      } catch (error) {
        if (window.partnerMetricsTrack) window.partnerMetricsTrack('detail_load_failed', { block });
        if (hasCache) return;""",
        1,
    )
    patched = patched.replace(
        """    document.getElementById('close').addEventListener('click', () => tg ? tg.close() : history.back());""",
        """    document.getElementById('close').addEventListener('click', () => {
      if (window.partnerMetricsTrack) window.partnerMetricsTrack('detail_webapp_closed', { block });
      tg ? tg.close() : history.back();
    });""",
        1,
    )
    patched = patched.replace(
        """      if (tg) { tg.ready(); tg.expand(); }
      load();""",
        """      if (tg) { tg.ready(); tg.expand(); }
      if (window.partnerMetricsTrack) window.partnerMetricsTrack('detail_webapp_opened', { block });
      load();""",
        1,
    )
    return patched


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return

    webapp.WEBAPP_HTML = _patch_profile_html(webapp.WEBAPP_HTML)
    webapp.DETAIL_WEBAPP_HTML = _patch_detail_html(webapp.DETAIL_WEBAPP_HTML)

    original_send_html = webapp.WebAppHandler._send_html
    original_do_post = webapp.WebAppHandler.do_POST

    def send_html_with_metrica(self: webapp.WebAppHandler, html: str) -> None:
        if "partner-yandex-metrica" not in html:
            html = html.replace("</head>", f"{_client_script()}\n</head>", 1)
        original_send_html(self, html)

    def do_post_with_analytics(self: webapp.WebAppHandler) -> None:
        path = urlparse(self.path).path.rstrip("/") or "/"
        if path != "/api/analytics":
            original_do_post(self)
            return
        try:
            payload = self._read_json()
            user_id = webapp._validate_init_data(str(payload.get("initData", "")))
            event_name = str(payload.get("event", "")).strip()
            if event_name not in _ALLOWED_EVENTS or not _EVENT_RE.fullmatch(event_name):
                raise ValueError("Unsupported analytics event")
            event_payload = _sanitize_payload(payload.get("payload"))
            webapp.get_store().track_event(user_id, event_name, event_payload)
            self._send_json({"ok": True}, status=202)
        except Exception as exc:
            logger.warning("WEBAPP_ANALYTICS_ERROR: %s", exc)
            self._send_json({"ok": False, "error": "analytics_rejected"}, status=400)

    webapp.WebAppHandler._send_html = send_html_with_metrica
    webapp.WebAppHandler.do_POST = do_post_with_analytics
    _INSTALLED = True
    logger.info("YANDEX_METRICA: webapp analytics installed; counter=%s", _counter_id() or "disabled")
