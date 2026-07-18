from app.ad_landing import build_landing_html


def test_ad_landing_has_manual_telegram_transition() -> None:
    html = build_landing_html("https://t.me/example_bot?start=ad_token123", True, "token123")

    assert "Получить первый разбор бесплатно" in html
    assert "Как он чувствует заботу — и почему иногда закрывается" in html
    assert "Причина дистанции" in html
    assert "Всего три шага" in html
    assert 'href="/go/out?token=token123&amp;variant=relationship"' in html
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


def test_money_landing_is_honest_and_tracks_variant() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="money")

    assert "Почему разговор о деньгах с ним быстро становится напряжённым?" in html
    assert "не финансовый прогноз" in html
    assert "расчёт денежной совместимости" in html
    assert "variant: landingVariant" in html
    assert 'data-landing-variant="money"' in html


def test_message_landing_promises_concrete_free_result() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="message")

    assert "Не знаете, что ему написать, чтобы не усилить дистанцию?" in html
    assert "Получить бесплатную подсказку и фразу" in html
    assert "Фраза не управляет человеком" in html
    assert 'data-landing-variant="message"' in html
