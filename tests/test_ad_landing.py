from app.ad_landing import build_landing_html


def test_ad_landing_has_manual_telegram_transition() -> None:
    html = build_landing_html("https://t.me/example_bot?start=ad_token123", True, "token123")

    assert "Получить первый разбор бесплатно" in html
    assert "Как он чувствует заботу — и почему иногда закрывается" in html
    assert "Причина дистанции" in html
    assert "Всего три шага" in html
    assert 'href="/go/out?token=token123"' in html
    assert "setTimeout(openBot" not in html
    assert "event.preventDefault()" not in html
    assert "document.querySelectorAll('[data-open-bot]')" in html
    assert "partnerMetricsTrack('landing_to_bot'" in html
    assert "точное время рождения не нужно" in html
    assert "Вот как выглядит подсказка" in html
    assert "Хочу спокойно понять тебя, а не спорить" in html
    assert "полная карта отношений — 199 ₽" in html


def test_unattributed_landing_keeps_direct_telegram_link() -> None:
    html = build_landing_html("https://t.me/example_bot", False)

    assert 'href="https://t.me/example_bot"' in html
    assert "/go/out?token=" not in html
