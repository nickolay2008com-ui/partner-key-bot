from app.ad_landing import build_landing_html


def test_ad_landing_has_manual_telegram_transition() -> None:
    html = build_landing_html("https://t.me/example_bot?start=ad_token123", True, "token123")

    assert "Получить первый вариант бесплатно" in html
    assert "Почему мужчина отдаляется в важные моменты" in html
    assert "Как хочется сказать" in html
    assert "Смягчить мою фразу" in html
    assert 'href="/go/out?token=token123&amp;variant=relationship"' in html
    assert "setTimeout(openBot" not in html
    assert "event.preventDefault()" not in html
    assert "document.querySelectorAll('[data-open-bot]')" in html
    assert "partnerMetricsTrack('landing_to_bot'" in html
    assert "нужны имя и дата рождения" in html
    assert "demo_transformed" in html
    assert "Как сохранить смысл и снизить напряжение" in html
    assert "Дополнительные главы" in html


def test_unattributed_landing_keeps_direct_telegram_link() -> None:
    html = build_landing_html("https://t.me/example_bot", False)

    assert 'href="https://t.me/example_bot"' in html
    assert "/go/out?token=" not in html


def test_money_landing_is_honest_and_tracks_variant() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="money")

    assert "Как говорить о деньгах, не задевая мужчину" in html
    assert "Бот не обещает доход" in html
    assert "Перевести упрёк в договорённость" in html
    assert "variant: landingVariant" in html
    assert 'data-landing-variant="money"' in html


def test_message_landing_promises_concrete_free_result() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="message")

    assert "Сообщение, которое можно отправить ему сегодня" in html
    assert "Получить мой вариант сообщения" in html
    assert "Отправлять его или нет — решаете вы" in html
    assert 'data-landing-variant="message"' in html


def test_five_trigger_landings_have_distinct_promises_and_tracking() -> None:
    expected = {
        "after_conflict": "Что написать мужчине после ссоры",
        "care": "Какую заботу мужчина действительно замечает",
        "mistake": "Проверьте слова до сложного разговора",
        "contribution": "Почему ваш вклад в семью остаётся незамеченным",
        "growth": "Как говорить о росте дохода без давления",
    }

    for variant, promise in expected.items():
        html = build_landing_html("https://t.me/example_bot", False, variant=variant)
        assert promise in html
        assert f'data-landing-variant="{variant}"' in html
        assert "Первая персональная подсказка бесплатно" in html
        assert "version: 'mini_v1'" in html


def test_growth_landing_does_not_promise_income() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="growth")

    assert "Подсказка не увеличивает доход сама" in html
    assert "нужны решения и реальные действия" in html


def test_instruction_landing_has_four_interactive_chapters() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="instruction")

    assert "Инструкция к любимому мужчине" in html
    assert "Спокойствие" in html
    assert "Любовь" in html
    assert "Цели" in html
    assert "Рост" in html
    assert "instruction_chapter_opened" in html
    assert 'data-landing-variant="instruction"' in html


def test_instruction_focus_variants_have_distinct_offers() -> None:
    expected = {
        "instruction_care": "Какая забота действительно доходит до вашего мужчины",
        "instruction_growth": "Как стать командой в целях и деньгах",
        "instruction_today": "Что написать ему сейчас, не усиливая дистанцию",
    }

    for variant, headline in expected.items():
        html = build_landing_html("https://t.me/example_bot", False, variant=variant)
        assert headline in html
        assert f'data-landing-variant="{variant}"' in html


def test_success_landing_promises_support_not_control() -> None:
    html = build_landing_html("https://t.me/example_bot", False, variant="make_successful")

    assert "Какая поддержка помогает ему действовать самостоятельно" in html
    assert "реакцию на советы" in html
    assert "Вы не отвечаете за его успех" in html
    assert 'data-landing-variant="make_successful"' in html


def test_intent_landings_leave_a_personal_question_for_telegram() -> None:
    for variant in ("instruction_care", "instruction_growth", "instruction_today", "make_successful"):
        html = build_landing_html("https://t.me/example_bot", True, "token123", variant=variant)
        assert "landing_choice_selected" in html
        assert "setLandingChoice" in html
        assert "важно уточнить именно про него" in html
