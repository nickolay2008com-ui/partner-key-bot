from __future__ import annotations

import gzip

from app import webapp


def test_telegram_sdk_does_not_block_html_parsing() -> None:
    for html in (webapp.WEBAPP_HTML, webapp.DETAIL_WEBAPP_HTML):
        assert 'id="telegram-web-app-sdk" async' in html
        assert "waitForTelegramSdk" in html
        assert "<script defer src=\"https://telegram.org/js/telegram-web-app.js\"" not in html


def test_detail_cache_is_rendered_before_waiting_for_telegram_sdk() -> None:
    cache_position = webapp.DETAIL_WEBAPP_HTML.index("renderCachedDetail();")
    sdk_position = webapp.DETAIL_WEBAPP_HTML.index("tg = await waitForTelegramSdk();")

    assert cache_position < sdk_position


def test_large_responses_are_compressed_when_browser_supports_gzip() -> None:
    body = ("эмоциональный мост " * 300).encode()

    compressed, encoding = webapp._compress_response(body, "br, gzip, deflate")

    assert encoding == "gzip"
    assert gzip.decompress(compressed) == body
    assert len(compressed) < len(body) / 3


def test_small_responses_skip_compression() -> None:
    body = b'{"ok":true}'

    encoded, encoding = webapp._compress_response(body, "gzip")

    assert encoded == body
    assert encoding is None
