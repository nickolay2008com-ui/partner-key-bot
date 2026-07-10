from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.astro.calculator import Placement
from app.astro.product_blocks import format_couple_moon_bridge_short_card, format_moon_variant_cards
from app.astro.report import PartnerReport
from app.relationship_practice import format_star_goal


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


def test_bridge_summary_keyboard_separates_full_bridge_cta_from_menu() -> None:
    from app.woman_flow import bridge_summary_keyboard, read_menu_keyboard

    bridge_buttons = [button.text for row in bridge_summary_keyboard().inline_keyboard for button in row]
    menu_buttons = [button.text for row in read_menu_keyboard().inline_keyboard for button in row]

    assert bridge_buttons == ["💞 Открыть полный эмоциональный мост"]
    assert "💞 Открыть полный эмоциональный мост" not in menu_buttons
    assert "1️⃣ Венера: как включить его нежность" in menu_buttons
    assert "2️⃣ Меркурий: слова, которые он слышит" in menu_buttons
    assert "3️⃣ Марс: как дать ему силу действовать" in menu_buttons
    assert "4️⃣ Юпитер: куда вести вашу пару" in menu_buttons


def test_detail_card_keyboard_embeds_read_menu_instead_of_back_button() -> None:
    from app.woman_flow import detail_card_keyboard

    keyboard = detail_card_keyboard("moon").inline_keyboard
    button_texts = [button.text for row in keyboard for button in row]

    assert button_texts[0] == "🌙 Луна (глубже)"
    assert "⬅️ Назад к карте" not in button_texts
    assert "1️⃣ Луна: где ему спокойно" not in button_texts
    assert "1️⃣ Венера: как включить его нежность" in button_texts
    assert "4️⃣ Юпитер: куда вести вашу пару" in button_texts
    assert "💞 Новый разбор" in button_texts


def test_premium_keyboard_uses_read_menu_label() -> None:
    from app.woman_flow import premium_keyboard

    button_texts = [button.text for row in premium_keyboard("details").inline_keyboard for button in row]

    assert "📖 Меню" in button_texts
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
    assert locked_buttons[0] == "🔓 Открыть за 50 ₽ · ваша планета бесплатно"

    paywall = premium_paywall_text("planet_venus")
    assert "за 50 ₽" in paywall
    assert "женская Венера" in paywall
    assert "ваша планета бесплатно" in paywall

    buy_buttons = [button.text for row in premium_keyboard("planet_venus").inline_keyboard for button in row]
    assert "Открыть планету за 50 ₽ · ваша бесплатно" in buy_buttons


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
