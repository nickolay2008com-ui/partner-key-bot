from datetime import date
from unittest import TestCase

from app.astro.calculator import calculate_partner_chart, calculate_placement
from app.astro.report import build_partner_report


class RetrogradeCalculationTest(TestCase):
    def test_mercury_retrograde_is_detected_from_swiss_ephemeris_speed(self) -> None:
        placement = calculate_placement(date(2024, 8, 5), "mercury")

        self.assertIs(placement.is_retrograde, True)

    def test_direct_mercury_is_not_marked_retrograde(self) -> None:
        placement = calculate_placement(date(2024, 7, 20), "mercury")

        self.assertIs(placement.is_retrograde, False)

    def test_retrograde_station_day_is_marked_as_time_sensitive(self) -> None:
        report = build_partner_report(calculate_partner_chart(date(2024, 8, 5)), "Тест")

        self.assertIs(report.placements["mercury"]["is_retrograde"], True)
        self.assertEqual(report.placements["mercury"]["motion_status"], "changed_during_day")
        self.assertIn("Меркурий: Дева, стихия Земля, смена движения в течение дня", report.text)
        self.assertIn("↩️ Точность ретроградности (Меркурий)", report.text)

    def test_stable_retrograde_status_is_reflected_in_report_text(self) -> None:
        report = build_partner_report(calculate_partner_chart(date(2024, 8, 10)), "Тест")

        self.assertIs(report.placements["mercury"]["is_retrograde"], True)
        self.assertEqual(report.placements["mercury"]["motion_status"], "stable_retrograde")
        self.assertIn("Меркурий: Дева, стихия Земля, ретроградное положение", report.text)
        self.assertIn("↩️ Ретроградность (Меркурий)", report.text)
