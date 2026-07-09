from datetime import date
from unittest import TestCase
from unittest.mock import patch

from app.astro.calculator import Placement
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
