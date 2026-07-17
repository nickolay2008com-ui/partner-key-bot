from __future__ import annotations

from types import SimpleNamespace

import app.entertaining_flow as flow


PLANETS = {
    "moon": ("🌙", "Луна"),
    "venus": ("💗", "Венера"),
    "mercury": ("🗣", "Меркурий"),
    "mars": ("🔥", "Марс"),
    "jupiter": ("🪐", "Юпитер"),
}


def test_free_hint_label_is_inserted_after_title_for_every_planet(monkeypatch) -> None:
    def fake_card(report, key: str) -> str:
        emoji, title = PLANETS[key]
        return f"{emoji} Новая серия: {title}\n\nСегодня в главной роли — Любимый."

    monkeypatch.setattr(flow.fun, "format_planet_short_card", fake_card)

    for key, (emoji, title) in PLANETS.items():
        text = flow._planet_short_card_with_free_hint(SimpleNamespace(), key)
        assert text.splitlines()[:5] == [
            f"{emoji} Новая серия: {title}",
            "",
            "🎁 Бесплатная подсказка",
            "",
            "Сегодня в главной роли — Любимый.",
        ]
        assert text.count(flow.FREE_HINT_LABEL) == 1


def test_free_hint_label_is_not_duplicated(monkeypatch) -> None:
    original = "🔥 Новая серия: Марс\n\n🎁 Бесплатная подсказка\n\nТекст карточки."
    monkeypatch.setattr(flow.fun, "format_planet_short_card", lambda report, key: original)

    assert flow._planet_short_card_with_free_hint(SimpleNamespace(), "mars") == original
