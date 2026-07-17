from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.astro.calculator import Placement
from app.astro.product_blocks import (
    format_couple_moon_bridge,
    format_couple_moon_bridge_short_card,
    format_moon_variant_cards,
)
from app.astro.report import PartnerReport
from app.relationship_practice import format_daily_broadcast_key, format_star_goal


class StarGoalFormatTest(TestCase):
    def test_star_goal_leads_with_practical_couple_action_before_astro_details(self) -> None:
        placements = {
            "sun": Placement("sun", "Солнце", 0.0, "aries", "Овен", "fire", "Огонь", False),
            "moon": Placement("moon", "Луна", 90.0, "taurus", "Телец", "earth", "Земля", False),
            "venus": Placement("venus", "Венера", 120.0, "leo", "Лев", "fire", "Огонь", False),
            "mars": Placement("mars", "Марс", 180.0, "gemini", "Близнецы", "air", "Воздух", False),
        }

        with (
            patch("app.relationship_practice._today", return_value=date(2026, 7, 9)),
            patch("app.relationship_practice.calculate_placement", side_effect=lambda _day, planet: placements[planet]),
        ):
            text = format_star_goal("UTC")

        self.assertIn("Главное: показать заботу делом.", text)
        self.assertIn("Что сделать сегодня: выбери одну практическую вещь", text)
        self.assertIn("Для процветания пары: укрепляйте стабильность пары", text)
        self.assertIn("Астро-детали коротко:", text)
        self.assertLess(text.index("Главное:"), text.index("Астро-детали коротко:"))
        self.assertNotIn("Небо сегодня:", text)


def test_daily_broadcast_key_matches_practical_daily_card_without_extra_astrology() -> None:
    text = format_daily_broadcast_key("UTC", date(2026, 7, 9))

    assert "🔑 Ключ к контакту на сегодня — 09.07.2026" in text
    assert "Мини-действие на 24 часа:" in text
    assert "Готовая мягкая фраза:" in text
    assert "Как понять, что сработало:" in text
    assert "Если хочется точнее — сделайте разбор пары: /partner" in text
    assert "Планета-фокус" not in text
    assert "Код дня" not in text


def _report(
    name: str,
    sign_key: str,
    sign_ru: str,
    element: str,
    element_ru: str,
    status: str = "exact",
    variants: list[dict[str, object]] | None = None,
) -> PartnerReport:
    moon = {
        "sign_key": sign_key,
        "sign_ru": sign_ru,
        "element": element,
        "element_ru": element_ru,
        "is_retrograde": False,
    }
    base = {"sign_key": "taurus", "sign_ru": "Телец", "element": "earth", "element_ru": "Земля", "is_retrograde": False}
    return PartnerReport(
        partner_name=name,
        birth_date="1993-04-12",
        moon_status=status,
        emotional_language=element,
        emotional_language_title="ритм",
        placements={"moon": moon, "venus": base, "mercury": base, "mars": base, "jupiter": base},
        summary="",
        text="",
        message_templates=[],
        moon_variants=variants or [],
    )


def test_full_couple_moon_bridge_has_emotional_copywriting_and_practical_24h_plan() -> None:
    man = _report("Андрей", "aries", "Овен", "fire", "Огонь")
    woman = _report("Анна", "cancer", "Рак", "water", "Вода")

    text = format_couple_moon_bridge(man, woman)

    assert "эмоциональная карта входа друг к другу" in text
    assert "способ сравнить два привычных ритма близости" in text
    assert "Как пользоваться этим мостом ближайшие 24 часа" in text
    assert "Хороший мост держится на двух берегах" in text


def test_couple_moon_bridge_short_card_points_to_full_html() -> None:
    man = _report("Андрей", "aries", "Овен", "fire", "Огонь")
    woman = _report("Анна", "cancer", "Рак", "water", "Вода")

    text = format_couple_moon_bridge_short_card(man, woman)

    assert "Эмоциональный мост: главное" in text
    assert "Полную карту моста" in text
    assert "его Луна в Овен" in text


def test_couple_moon_bridge_short_card_leads_with_benefit_before_technical_note() -> None:
    variants = [
        {"sign_key": "aries", "sign_ru": "Овен", "element": "fire", "element_ru": "Огонь"},
        {"sign_key": "taurus", "sign_ru": "Телец", "element": "earth", "element_ru": "Земля"},
    ]
    man = _report("Андрей", "aries", "Овен", "fire", "Огонь", "changed_during_day", variants)
    woman = _report("Анна", "cancer", "Рак", "water", "Вода")

    text = format_couple_moon_bridge_short_card(man, woman)

    assert "Техническое уточнение" in text
    assert text.index("Коротко:") < text.index("Техническое уточнение")
    assert text.index("Что сделать сейчас:") < text.index("Техническое уточнение")


def test_couple_moon_bridge_can_omit_transition_variants_for_webapp_swipes() -> None:
    variants = [
        {"sign_key": "aries", "sign_ru": "Овен", "element": "fire", "element_ru": "Огонь"},
        {"sign_key": "taurus", "sign_ru": "Телец", "element": "earth", "element_ru": "Земля"},
    ]
    man = _report("Андрей", "aries", "Овен", "fire", "Огонь", "changed_during_day", variants)
    woman = _report("Анна", "cancer", "Рак", "water", "Вода")

    text = format_couple_moon_bridge(man, woman, include_transition_variants=False)

    assert "Точность Луны" in text
    assert "Возможные варианты описания без точного времени рождения" not in text
    assert "Если Он:" not in text


def test_moon_variant_cards_include_all_transition_combinations() -> None:
    variants = [
        {"sign_key": "aries", "sign_ru": "Овен", "element": "fire", "element_ru": "Огонь"},
        {"sign_key": "taurus", "sign_ru": "Телец", "element": "earth", "element_ru": "Земля"},
    ]
    man = _report("Андрей", "aries", "Овен", "fire", "Огонь", "changed_during_day", variants)
    woman = _report(
        "Анна",
        "cancer",
        "Рак",
        "water",
        "Вода",
        "changed_during_day",
        [
            {"sign_key": "cancer", "sign_ru": "Рак", "element": "water", "element_ru": "Вода"},
            {"sign_key": "leo", "sign_ru": "Лев", "element": "fire", "element_ru": "Огонь"},
        ],
    )

    cards = format_moon_variant_cards(man, woman)

    assert len(cards) == 4
    assert cards[0]["title"].startswith("Он:")
    assert all("Фраза-мост" in card["text"] for card in cards)


def test_message_guidance_is_general_and_not_ready_script() -> None:
    from app.astro.report import format_message_guidance

    report = _report("Андрей", "taurus", "Телец", "earth", "Земля")

    text = format_message_guidance(report)

    assert "общий ориентир" in text
    assert "Смысл сообщения:" in text
    assert "Цель сообщения:" in text
    assert "Структура сообщения:" in text
    assert "Не нужен идеальный готовый текст" in text
    assert "Вариант 1" not in text
    assert "GPT" not in text


def test_bridge_summary_and_current_menu_keep_the_approved_actions() -> None:
    from app.woman_flow import bridge_summary_keyboard, read_menu_keyboard

    bridge_buttons = [button.text for row in bridge_summary_keyboard().inline_keyboard for button in row]
    menu_buttons = [button.text for row in read_menu_keyboard().inline_keyboard for button in row]

    assert bridge_buttons == ["💞 Открыть полный эмоциональный мост"]
    assert menu_buttons.count("💞 Открыть полный эмоциональный мост") == 1
    assert "📖 Полная карта отношений — 199 ₽" in menu_buttons
    assert "🪐 Выбрать отдельную тему — 50 ₽" in menu_buttons


def test_detail_card_keyboard_keeps_content_cta_separate_from_full_menu() -> None:
    from app.woman_flow import detail_card_keyboard

    keyboard = detail_card_keyboard("moon").inline_keyboard
    button_texts = [button.text for row in keyboard for button in row]

    assert button_texts == ["🌙 Луна (глубже)", "📖 Меню"]
    assert "⬅️ Назад к карте" not in button_texts
    assert "1️⃣ Венера: его язык симпатии" not in button_texts
    assert "4️⃣ Юпитер: смысл и направление роста" not in button_texts
    assert "💞 Новый разбор" not in button_texts


def test_after_free_actions_can_be_sent_as_separate_button_blocks() -> None:
    from app.woman_flow import after_free_deep_keyboard, after_free_followup_keyboard

    deep_buttons = [button.text for row in after_free_deep_keyboard().inline_keyboard for button in row]
    followup_buttons = [button.text for row in after_free_followup_keyboard().inline_keyboard for button in row]

    assert deep_buttons == ["🌙 Подробнее о его Луне"]
    assert followup_buttons == ["💞 Сравнить наши ритмы", "🔄 Другой разбор"]
    assert "💞 Сравнить наши ритмы" not in deep_buttons
    assert "🔄 Другой разбор" not in deep_buttons


def test_premium_keyboard_returns_to_product_choice() -> None:
    from app.woman_flow import premium_keyboard

    button_texts = [button.text for row in premium_keyboard("details").inline_keyboard for button in row]

    assert "← Вернуться к выбору" in button_texts
    assert "🪐 Выбрать одну тему за 50 ₽" in button_texts
    assert "⬅️ Назад к карте" not in button_texts


def test_planet_paywall_is_packaged_as_50_rub_with_free_woman_planet(monkeypatch) -> None:
    from types import SimpleNamespace

    from app.payments import get_product
    import app.woman_flow as woman_flow
    from app.woman_flow import detail_card_keyboard, premium_keyboard, premium_paywall_text

    monkeypatch.setattr(woman_flow, "settings", SimpleNamespace(yookassa_enabled=True))

    product = get_product("planet_venus")
    assert product is not None
    assert product.rubles == 50

    locked_buttons = [
        button.text for row in detail_card_keyboard("venus", locked=True).inline_keyboard for button in row
    ]
    assert locked_buttons == ["🔓 Открыть Венеру за 50 ₽", "👀 Что внутри", "⬅️ К планетам"]

    paywall = premium_paywall_text("planet_venus")
    assert "Стоимость: 50 ₽" in paywall
    assert "женская Венера" in paywall
    assert "Разбор останется в этом чате" in paywall

    buy_buttons = [button.text for row in premium_keyboard("planet_venus").inline_keyboard for button in row]
    assert "🔓 Открыть Венеру за 50 ₽" in buy_buttons
    assert "👀 Бесплатная подсказка по Венере" in buy_buttons
    assert "⬅️ К планетам" in buy_buttons
    assert "📖 Меню" not in buy_buttons


def test_planet_payment_recovery_keeps_user_in_current_planet_context() -> None:
    from app.woman_flow import payment_recovery_keyboard, yookassa_payment_keyboard

    recovery_buttons = [
        button.text for row in payment_recovery_keyboard("planet_jupiter", "pay_1").inline_keyboard for button in row
    ]
    assert recovery_buttons == [
        "✅ Проверить оплату ещё раз",
        "🔁 Создать ссылку заново",
        "🛟 Мои покупки",
        "👀 Бесплатная подсказка по Юпитеру",
        "⬅️ К планетам",
    ]

    payment_buttons = [
        button.text
        for row in yookassa_payment_keyboard("planet_jupiter", "pay_1", "https://pay.example").inline_keyboard
        for button in row
    ]
    assert payment_buttons == ["Оплатить в ЮKassa", "✅ Проверить оплату", "🛟 Мои покупки", "⬅️ К планетам"]


def test_free_preview_uses_instruction_positioning_visible_after_birth_date() -> None:
    from app.astro.report import format_free_preview

    report = _report("Андрей", "gemini", "Близнецы", "air", "Воздух")

    text = format_free_preview(report)

    assert "💞 Инструкция к любимому мужчине" in text
    assert "🔑 Первый ключ к его эмоциональному комфорту" in text
    assert "🌙 Его эмоциональная стихия — Воздух." in text
    assert "✨ Что это даёт вам на практике" in text
    assert "🧭 Его ключ:" in text
    assert "🤍 Мягкий ключ на сегодня" in text
    assert "🔎 Как проверить, работает ли этот ключ" in text
    assert "💞 Хотите увидеть ваш общий эмоциональный мост?" in text
    assert "меньше игры в угадайку" in text
    assert "**" not in text


def test_message_guidance_shows_saved_live_templates_when_report_has_them() -> None:
    from app.astro.meanings import MESSAGE_TEMPLATES
    from app.astro.report import format_message_guidance

    report = _report("Андрей", "gemini", "Близнецы", "air", "Воздух")
    report = PartnerReport(**{**report.to_dict(), "message_templates": MESSAGE_TEMPLATES["air"]})

    text = format_message_guidance(report)

    assert "Варианты живого сообщения:" in text
    assert "квеста «угадай по молчанию»" in text
    assert "• " in text


def test_detail_webapp_urls_use_separate_fast_pages() -> None:
    from app.woman_flow import detail_webapp_info

    assert detail_webapp_info("venus").url.endswith("/webapp/detail/venus")
    assert detail_webapp_info("bridge").url.endswith("/webapp/detail/bridge")


def test_sales_free_preview_discloses_stable_moon_basis() -> None:
    from app.partner_flow import format_free_preview

    text = format_free_preview(_report("Андрей", "taurus", "Телец", "earth", "Земля", status="stable"))

    assert "(Он: Луна в Тельце, Земля)" in text
    assert "только один ориентир" in text
    assert "сравнить два равноправных ритма" in text


def test_sales_free_preview_discloses_both_moon_signs_on_transition_day() -> None:
    from app.partner_flow import format_free_preview

    variants = [
        {"sign_key": "taurus", "sign_ru": "Телец", "element": "earth", "element_ru": "Земля"},
        {"sign_key": "gemini", "sign_ru": "Близнецы", "element": "air", "element_ru": "Воздух"},
    ]
    report = _report("Андрей", "taurus", "Телец", "earth", "Земля", status="changed_during_day", variants=variants)

    text = format_free_preview(report)

    assert "В эту дату Луна меняла знак" in text
    assert "Луна в Тельце, Земля" in text
    assert "Луна в Близнецах, Воздух" in text


def test_relationship_menu_uses_task_based_product_hierarchy() -> None:
    from app.entertaining_flow import _relationship_menu_keyboard

    buttons = [button.text for row in _relationship_menu_keyboard().inline_keyboard for button in row]

    assert buttons == [
        "💞 Открыть полный эмоциональный мост",
        "✍️ 2 варианта сообщения — 149 ₽",
        "📖 Полная карта отношений — 199 ₽",
        "🪐 Выбрать отдельную тему — 50 ₽",
        "🔄 Новый разбор",
    ]


def test_message_paywall_matches_two_existing_templates() -> None:
    from app.woman_flow import premium_paywall_text

    text = premium_paywall_text("message")

    assert "2 варианта сообщения" in text
    assert "два черновика" in text
    assert "Стоимость: 149 ₽" in text
    assert "гарантия ответа" in text
    assert "3 готовых" not in text
