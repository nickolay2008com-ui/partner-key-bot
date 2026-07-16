from app.ad_landing import build_landing_html


def test_ad_landing_has_manual_telegram_transition() -> None:
    html = build_landing_html("https://t.me/example_bot?start=ad_token123", True)

    assert "Открыть Telegram и нажать «Запустить»" in html
    assert "После открытия Telegram нажмите «Запустить»" in html
    assert "setTimeout(openBot" not in html
    assert "event.preventDefault()" in html
    assert "window.setTimeout" in html
    assert "landing_to_bot" in html
    assert "полная карта отношений — 199 ₽" in html
