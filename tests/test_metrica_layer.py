from __future__ import annotations

import app.webapp as webapp
from app.metrica_layer import (
    _client_script,
    _patch_detail_html,
    _patch_profile_html,
    _sanitize_payload,
)


def test_client_script_initializes_safe_yandex_metrica_tag() -> None:
    script = _client_script(12345678)

    assert "https://mc.yandex.ru/metrika/tag.js" in script
    assert "window.ym(12345678, 'init'" in script
    assert "'reachGoal'" in script
    assert "webvisor: false" in script
    assert "sendTitle: false" in script
    assert "bridge_opened" in script
    assert "full_map_opened" in script
    assert "planet_opened" in script


def test_client_script_keeps_internal_analytics_when_counter_is_disabled() -> None:
    script = _client_script(0)

    assert "const METRICA_ID = null" in script
    assert "'/api/analytics'" in script
    assert "partnerMetricsTrack" in script


def test_profile_html_routes_existing_events_to_shared_tracker() -> None:
    patched = _patch_profile_html(webapp.WEBAPP_HTML)

    assert "window.partnerMetricsTrack(eventName, payload)" in patched
    assert "track('profile_webapp_opened')" in patched
    assert "track('profile_saved'" in patched
    assert "track('profile_load_failed')" in patched
    assert "track('profile_save_failed')" in patched


def test_detail_html_tracks_open_load_error_and_close() -> None:
    patched = _patch_detail_html(webapp.DETAIL_WEBAPP_HTML)

    assert "detail_webapp_opened" in patched
    assert "detail_loaded" in patched
    assert "detail_load_failed" in patched
    assert "detail_webapp_closed" in patched
    assert "detailMetricSent" in patched


def test_analytics_payload_drops_private_or_unbounded_values() -> None:
    payload = _sanitize_payload(
        {
            "block": "bridge",
            "hasSelfDate": True,
            "price": 199,
            "bad-key": "ignored",
            "nested": {"name": "private"},
            "longValue": "x" * 500,
        }
    )

    assert payload == {
        "block": "bridge",
        "hasSelfDate": True,
        "price": 199,
        "longValue": "x" * 120,
    }
