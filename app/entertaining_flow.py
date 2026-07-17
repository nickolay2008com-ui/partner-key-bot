from __future__ import annotations

import app.partner_flow as current
import app.webapp as webapp
import app.woman_flow as base
from app import payment_checkout
from app.astro import bridge_upgrade as bridge
from app.astro import entertaining_blocks as fun


FREE_HINT_LABEL = "🎁 Бесплатная подсказка"


def _planet_short_card_with_free_hint(report, key: str) -> str:
    """Label every Telegram planet teaser as a free hint without duplicating text."""
    text = fun.format_planet_short_card(report, key)
    if FREE_HINT_LABEL in text:
        return text

    title, separator, body = text.partition("\n\n")
    if not separator:
        return f"{text}\n\n{FREE_HINT_LABEL}"
    return f"{title}\n\n{FREE_HINT_LABEL}\n\n{body}"


def _fix_pair_you_lines(text: str) -> str:
    replacements = {
        "Вы: Его чувства": "Вы: Ваши чувства",
        "Вы: Его Венера": "Вы: Ваша Венера",
        "Вы: Он мыслит": "Вы мыслите",
        "Вы: Он слышит": "Вы слышите",
        "Вы: Его Марс": "Вы: Ваш Марс",
        "Вы: Он растёт": "Вы растёте",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _fix_woman_portrait(text: str, woman_name: str) -> str:
    marker = f"👤 {woman_name}: ваша роль в отношениях"
    if marker not in text:
        return text
    before, after = text.split(marker, 1)
    replacements = {
        "Его чувства": "Ваши чувства",
        "Его Венера": "Ваша Венера",
        "Он мыслит": "Вы мыслите",
        "Он слышит": "Вы слышите",
        "Его Марс": "Ваш Марс",
        "Он растёт": "Вы растёте",
        "Что для него выглядит как любовь": "Что для вас выглядит как любовь",
        "Как устроен его переводчик": "Как устроен ваш переводчик",
        "Ради какого будущего он оживает": "Ради какого будущего вы оживаете",
    }
    for source, target in replacements.items():
        after = after.replace(source, target)
    return before + marker + after


def _couple_portraits(man_report, woman_report):
    return _fix_woman_portrait(fun.format_couple_portraits(man_report, woman_report), woman_report.partner_name)


def _couple_full_report(man_report, woman_report):
    return _fix_pair_you_lines(fun.format_couple_full_report(man_report, woman_report))


def _relationship_menu_keyboard(report_id: int = 0):
    details_product = base.get_product("details")
    message_product = base.get_product("message")
    details_price = f" — {details_product.rubles} ₽" if details_product else ""
    message_price = f" — {message_product.rubles} ₽" if message_product else ""
    return base.InlineKeyboardMarkup(
        [
            [
                base.InlineKeyboardButton(
                    "💞 Открыть полный эмоциональный мост",
                    callback_data=base._callback_with_report("p:bridge", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"✍️ 2 варианта сообщения{message_price}",
                    callback_data="message",
                )
            ],
            [
                base.InlineKeyboardButton(
                    f"📖 Полная карта отношений{details_price}",
                    callback_data=base._callback_with_report("p:full", report_id),
                )
            ],
            [
                base.InlineKeyboardButton(
                    "🪐 Выбрать отдельную тему — 50 ₽",
                    callback_data=base._callback_with_report("premium:planets", report_id),
                )
            ],
            [base.InlineKeyboardButton("🔄 Новый разбор", callback_data="start_man")],
        ]
    )


async def _relationship_menu_text(update, context) -> str:
    man_report = await base._load_latest_man_report(update, context)
    woman_report = base._load_report(context, base.LAST_WOMAN_REPORT)
    if woman_report is None:
        try:
            profile = await base._get_profile(update)
            self_birth_date = str(profile.get("self_birth_date", "")).strip()
            if self_birth_date:
                birth_date = base.parse_birth_date(self_birth_date)
                chart = await base.asyncio.to_thread(base.calculate_partner_chart, birth_date)
                woman_report = await base.asyncio.to_thread(
                    base.build_partner_report,
                    chart,
                    profile.get("self_name") or "вы",
                )
                base._save_report(context, base.LAST_WOMAN_REPORT, woman_report)
        except Exception:
            base.logger.exception("RELATIONSHIP_MENU_SELF_REPORT_FAILED")
    if man_report is None or woman_report is None:
        return "🧭 Что сейчас будет полезнее?"
    return (
        f"{bridge.format_relationship_menu_summary(man_report, woman_report)}\n\n"
        "🧭 Что сейчас будет полезнее?\n\n"
        "Мост покажет ваш базовый ритм. Дальше можно выбрать прикладной шаг, "
        "связную карту пяти уровней или одну отдельную тему."
    )


async def _send_bridge_teaser_with_menu(update, context, text: str) -> None:
    report_id = base._current_report_id(context)
    await base._send_long(update, context, text, reply_markup=base.bridge_summary_keyboard(report_id))
    await base._tracked_reply_text(
        update,
        context,
        await _relationship_menu_text(update, context),
        reply_markup=_relationship_menu_keyboard(report_id),
    )


_original_premium_offer = base.premium_offer


async def _premium_offer_with_relationship_menu(update, context) -> None:
    data = update.callback_query.data if update.callback_query else ""
    if (data or "").replace("premium:", "") != "back":
        await _original_premium_offer(update, context)
        return

    if update.callback_query:
        await update.callback_query.answer()
    await base._remember_user(update)
    if update.callback_query and update.callback_query.message:
        try:
            await update.callback_query.message.delete()
            base._forget_bot_message(context, update.callback_query.message)
        except Exception:
            pass
    await base._tracked_reply_text(
        update,
        context,
        await _relationship_menu_text(update, context),
        reply_markup=_relationship_menu_keyboard(base._current_report_id(context)),
    )


# Telegram cards use function references imported by woman_flow, while the WebApp
# keeps its own imported references. Patch both namespaces and leave calculations
# and storage intact.
base.format_planet_short_card = _planet_short_card_with_free_hint
base.format_couple_moon_bridge_short_card = bridge.format_couple_moon_bridge_short_card
base.format_couple_portraits_short_card = fun.format_couple_portraits_short_card
base.read_menu_keyboard = _relationship_menu_keyboard
base._send_bridge_teaser_with_menu = _send_bridge_teaser_with_menu
base.premium_offer = _premium_offer_with_relationship_menu

webapp.format_moon_detail = fun.format_moon_detail
webapp.format_moon_deep_detail = fun.format_moon_deep_detail
webapp.format_venus_detail = fun.format_venus_detail
webapp.format_mercury_detail = fun.format_mercury_detail
webapp.format_mars_detail = fun.format_mars_detail
webapp.format_jupiter_detail = fun.format_jupiter_detail
webapp.format_couple_moon_bridge = bridge.format_couple_moon_bridge
webapp.format_couple_portraits = _couple_portraits
webapp.format_couple_full_report = _couple_full_report
webapp.format_moon_variant_cards = fun.format_moon_variant_cards
webapp.DETAIL_LABELS.update(fun.DETAIL_LABELS)
webapp.DETAIL_LABELS["bridge"] = "💞 Эмоциональный мост"

_original_detail_text = webapp._detail_text


def _entertaining_detail_text(user_id: int, block: str, report_id: int = 0) -> str:
    normalized = webapp._normalize_detail_block(block)
    if normalized == "details":
        payload = (
            webapp.get_store().report_payload(user_id, report_id)
            if report_id > 0
            else webapp.get_store().latest_report_payload(user_id)
        )
        report = webapp._report_from_payload(payload)
        if report is None:
            raise ValueError("Сначала соберите разбор в боте — тогда здесь откроется история героя.")
        return fun.format_person_full_story(report)
    return _original_detail_text(user_id, normalized, report_id)


webapp._detail_text = _entertaining_detail_text
webapp.DETAIL_WEBAPP_HTML = (
    webapp.DETAIL_WEBAPP_HTML.replace(
        "partner-key-detail:${block}:v2",
        "partner-key-detail:${block}:v6",
    )
    .replace(
        "✨ Инструкция к любимому мужчине",
        "🎬 Астро Партнёр: новая серия",
    )
    .replace(
        "Это не сухой прогноз, а мягкая инструкция: какие слова, внимание и действия помогают ему раскрыться рядом с вами.",
        "Здесь планеты становятся героями понятной истории: узнаваемые сцены, лёгкая ирония и один эксперимент, который можно проверить в жизни.",
    )
    .replace(
        "Структура моста без повторов",
        "Как пользоваться эмоциональным мостом",
    )
    .replace(
        "Сначала выберите похожий эмоциональный сценарий, затем возьмите одну фразу и один следующий шаг. Так карта становится инструкцией, а не ещё одним длинным разбором.",
        "Сначала увидьте ритм каждого, затем выберите одну фразу и один совместный ритуал. Мост нужен не для ремонта отношений, а чтобы хорошее между вами легче повторялось.",
    )
    .replace(
        "Его вход в спокойствие",
        "Его ритм близости",
    )
    .replace(
        "Темп, тон или конкретика, при которых он меньше защищается и легче слышит вас.",
        "Атмосфера, темп и действия, через которые он особенно хорошо чувствует тепло и участие.",
    )
    .replace(
        "Ваш берег",
        "Ваш ритм близости",
    )
    .replace(
        "Что нужно вам для тепла: внимание, ясность, время, действие или бережная пауза.",
        "Какие сигналы помогают вам чувствовать надёжность, внимание и естественную близость.",
    )
    .replace(
        "Маленький тест",
        "Общий ритуал",
    )
    .replace(
        "Одна просьба или сообщение на 24 часа, после которого видно: стало ли больше контакта.",
        "Одно приятное действие, которое легко повторять и по которому видно: становится ли связь теплее для обоих.",
    )
)

# Add a receipt-aware YooKassa layer. The rest of the payment and entitlement
# mechanics remain in woman_flow.
payment_checkout.install(base)


def main() -> None:
    base.logger.info("BOT_BOOT: starting entertaining partner readings")
    current.main()


if __name__ == "__main__":
    main()
