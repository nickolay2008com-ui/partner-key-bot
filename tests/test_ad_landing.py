from app.ad_landing import build_landing_html


def test_ad_landing_has_manual_telegram_transition() -> None:
    html = build_landing_html("https://t.me/example_bot?start=ad_token123", True)

    assert "Получить бесплатный ключ в Telegram" in html
    assert "Откроется бот — нажмите «Запустить»" in html
    assert "setTimeout(openBot" not in html
    assert "event.preventDefault()" in html
    assert "document.querySelectorAll('[data-open-bot]')" in html
    assert "'reachGoal', 'landing_to_bot'" in html
    assert "window.setTimeout(openTelegram, 1200)" in html
    assert "Точное время необязательно" in html
    assert "Как выглядит подсказка" in html
    assert "Хочу спокойно понять тебя, а не спорить" in html
    assert "199 ₽" not in html
