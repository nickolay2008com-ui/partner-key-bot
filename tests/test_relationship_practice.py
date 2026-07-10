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


def test_bridge_summary_keyboard_keeps_planet_navigation_visible() -> None:
    from app.woman_flow import bridge_summary_keyboard

    keyboard = bridge_summary_keyboard().inline_keyboard
    button_texts = [button.text for row in keyboard for button in row]

    assert button_texts[0] == "💞 Открыть полный эмоциональный мост"
    assert "1️⃣ Луна: где ему спокойно" in button_texts
    assert "2️⃣ Венера: что включает тепло" in button_texts
    assert "3️⃣ Меркурий: как договориться" in button_texts
    assert "4️⃣ Марс: как поддержать действие" in button_texts
    assert "5️⃣ Юпитер: куда расти вместе" in button_texts
