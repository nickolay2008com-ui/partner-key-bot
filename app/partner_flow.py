from __future__ import annotations

import asyncio
import platform

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import ConversationHandler, ContextTypes

import app.woman_flow as base
from app.astro.sign_bridge import SIGN_PREPOSITIONAL


WELCOME_TEXT = """
💞 Астро Партнёр

Почему с одним человеком достаточно одной фразы, а с другим даже забота может прозвучать как давление?

Астро Партнёр переводит дату рождения в практическую карту отношений:

• что помогает человеку расслабиться и идти на контакт;
• что он воспринимает как любовь и поддержку;
• какие слова ему легче услышать;
• что может заставлять его закрываться;
• какой шаг можно попробовать уже сегодня.

🔑 Первый ключ вы получите бесплатно. Он покажет эмоциональный ритм мужчины, конкретную фразу и признак, по которому можно проверить подсказку в реальной жизни.

Затем добавьте свою дату, чтобы увидеть не «процент совместимости», а механику вашей пары: где вы совпадаете, где ждёте друг от друга разного и как построить между этим мост.

Без приговоров и обещаний судьбы. Только гипотезы, которые можно проверить по живой реакции.
""".strip()


FREE_PREVIEW_COPY: dict[str, dict[str, str]] = {
    "fire": {
        "element": "Огонь",
        "insight": (
            "Ему легче идти навстречу, когда в контакте есть живость, интерес и движение. "
            "Сначала искра и совместный шаг, потом серьёзный разговор."
        ),
        "works": "короткое приглашение, лёгкий флирт, прямой интерес, новое впечатление или совместное действие.",
        "closes": "холодные проверки, затяжное молчание и попытка сразу разобрать отношения по пунктам.",
        "phrase": "Мне хочется тебя увидеть. Давай выберемся куда-нибудь без тяжёлых тем?",
        "signal": "он быстрее отвечает, предлагает вариант или сам продолжает контакт.",
        "bridge": "что зажигает его, что важно вам и как сохранить живость без эмоциональных качелей.",
    },
    "earth": {
        "element": "Земля",
        "insight": (
            "Ему легче открываться через спокойствие, телесное тепло, надёжность и понятные поступки. "
            "Для него близость чаще начинается не с громких слов, а с ощущения: рядом безопасно и на вас можно опереться."
        ),
        "works": "спокойная встреча, вкусный ужин, прогулка, объятие, помощь делом или понятный совместный план.",
        "closes": "резкие исчезновения, хаос, проверки чувств и неопределённость без объяснений.",
        "phrase": "Хочу спокойно провести с тобой вечер. Давай без суеты поужинаем или прогуляемся?",
        "signal": "он расслабляется, становится теплее или охотнее соглашается на конкретный план.",
        "bridge": "что даёт опору ему, что необходимо вам и как создать надёжный ритм для двоих.",
    },
    "air": {
        "element": "Воздух",
        "insight": (
            "Ему легче открываться через разговор, ясность, юмор и ощущение пространства. "
            "Когда понятно, что от него хотят, ему проще отвечать честно и не уходить в дистанцию."
        ),
        "works": "короткое сообщение, спокойный вопрос, прогулка с разговором, лёгкий флирт или обсуждение планов.",
        "closes": "намёки, молчаливые обиды, контроль переписки и требование угадать скрытый смысл.",
        "phrase": "Хочу спокойно понять тебя, а не спорить. Как ты сам видишь нашу ситуацию?",
        "signal": "он начинает объяснять, задаёт встречный вопрос или предлагает обсудить тему дальше.",
        "bridge": "где ему нужна свобода, где вам нужна определённость и как говорить без игры в угадайку.",
    },
    "water": {
        "element": "Вода",
        "insight": (
            "Ему легче раскрываться через мягкость, принятие и эмоциональную безопасность. "
            "Правильные слова работают слабее, если в тоне чувствуется холод или нападение."
        ),
        "works": "спокойный голос, бережное сообщение, объятие, признание чувства или тихий разговор без обвинений.",
        "closes": "насмешка по больному, резкость, обесценивание чувств и давление на немедленный ответ.",
        "phrase": "Мне важен наш контакт. Я хочу понять, что ты чувствуешь, и не хочу на тебя давить.",
        "signal": "он становится мягче, говорит о чувствах или перестаёт защищаться и остаётся в разговоре.",
        "bridge": "что создаёт безопасность ему, что помогает вам чувствовать близость и как не утонуть в недосказанности.",
    },
}


def menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔑 Получить первый ключ бесплатно", callback_data="start_man")],
            [InlineKeyboardButton("🗂 Мои разборы", callback_data="history")],
            [InlineKeyboardButton("🛟 Мои покупки", callback_data="purchases")],
            [base.profile_button()],
        ]
    )


def welcome_menu(has_saved_reports: bool) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton("🔑 Получить первый ключ бесплатно", callback_data="start_man")]]
    if has_saved_reports:
        rows = [
            [InlineKeyboardButton("🔑 Начать новый разбор", callback_data="start_man")],
            [InlineKeyboardButton("🗂 Мои разборы", callback_data="history")],
        ]
    return InlineKeyboardMarkup(rows)


def after_free_deep_keyboard(report_id: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🌙 Подробнее о его Луне", web_app=base.detail_webapp_info("moon_deep", report_id))]]
    )


def after_free_followup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Сравнить наши ритмы", callback_data="add_me")],
            [InlineKeyboardButton("🔄 Другой разбор", callback_data="start_man")],
        ]
    )


def read_menu_keyboard(report_id: int = 0) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "1️⃣ Венера: его язык симпатии", callback_data=base._callback_with_report("p:venus", report_id)
                )
            ],
            [
                InlineKeyboardButton(
                    "2️⃣ Меркурий: как ему легче воспринимать разговор",
                    callback_data=base._callback_with_report("p:mercury", report_id),
                )
            ],
            [
                InlineKeyboardButton(
                    "3️⃣ Марс: как он проявляет инициативу", callback_data=base._callback_with_report("p:mars", report_id)
                )
            ],
            [
                InlineKeyboardButton(
                    "4️⃣ Юпитер: смысл и направление роста",
                    callback_data=base._callback_with_report("p:jupiter", report_id),
                )
            ],
            [
                InlineKeyboardButton(
                    "🔓 Полная карта отношений", callback_data=base._callback_with_report("p:full", report_id)
                )
            ],
            [
                InlineKeyboardButton(
                    "👤 Сильные места и уязвимости пары",
                    callback_data=base._callback_with_report("p:portrait", report_id),
                )
            ],
            [InlineKeyboardButton("✍️ 2 варианта сообщения — 149 ₽", callback_data="message")],
            [InlineKeyboardButton("🔄 Новый разбор", callback_data="start_man")],
        ]
    )


def _moon_basis(variant: dict[str, object]) -> str:
    sign = str(variant.get("sign_ru", "знак не определён"))
    element = str(variant.get("element_ru", "стихия не определена"))
    prepositional = SIGN_PREPOSITIONAL.get(sign, sign)
    return f"Луна в {prepositional}, {element}"


def _moon_variant_summary(variant: dict[str, object]) -> str:
    element = str(variant.get("element", "earth"))
    copy = FREE_PREVIEW_COPY.get(element, FREE_PREVIEW_COPY["earth"])
    return f"{_moon_basis(variant)} — {copy['insight']}"


def format_free_preview(report: base.PartnerReport) -> str:
    copy = FREE_PREVIEW_COPY.get(report.emotional_language, FREE_PREVIEW_COPY["earth"])
    moon = report.placements.get("moon", {})
    element = str(moon.get("element_ru", copy["element"])) if isinstance(moon, dict) else copy["element"]

    if report.moon_status == "changed_during_day" and len(report.moon_variants) >= 2:
        variants = "\n\n".join(f"• {_moon_variant_summary(item)}" for item in report.moon_variants[:2])
        return f"""
🔑 Первый ключ к {report.partner_name}

⚠️ В эту дату Луна меняла знак

Без точного времени рождения возможны два эмоциональных сценария:

{variants}

Не выбирайте вариант только потому, что один текст звучит красивее. Вспомните, что чаще помогает {report.partner_name} после тяжёлого дня, как он принимает заботу и как возвращается в контакт.

💞 Добавьте свою дату, чтобы сравнить оба варианта с вашим ритмом.
""".strip()

    basis = _moon_basis(moon) if isinstance(moon, dict) else f"Луна, {element}"

    return f"""
🔑 Первый ключ к {report.partner_name}

🌙 Его вероятный эмоциональный ритм — {element}
(Он: {basis})

{copy["insight"]}

✅ Что обычно работает
{copy["works"]}

⚠️ Что может закрывать контакт
{copy["closes"]}

🤍 Попробуйте сегодня
«{copy["phrase"]}»

🔎 Как проверить подсказку
Смотрите не на мгновенное согласие, а на повторяющуюся реакцию: {copy["signal"]}

Это не описание всей его личности. Луна даёт только один ориентир — привычный эмоциональный ритм.

💞 Следующий шаг
Добавьте свою дату, чтобы сравнить два равноправных ритма и найти шаг, который учитывает обоих.
""".strip()


async def start_man(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not base._is_authorized(update):
        await base._deny(update)
        return ConversationHandler.END

    await base._remember_user(update)
    await base._track_event(update, "partner_flow_started")
    await base._set_chat_menu_button(update, context)
    await base._clear_active_bot_messages(update, context)

    if update.callback_query:
        try:
            await update.callback_query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass

    base._clear_flow_state(context)
    profile_data = await base._get_profile(update)
    partner_name = profile_data.get("partner_name", "").strip()
    partner_birth_date = profile_data.get("partner_birth_date", "").strip()

    if partner_name and partner_birth_date:
        await base._tracked_reply_text(
            update,
            context,
            (
                f"У вас уже сохранён {partner_name}, дата рождения {partner_birth_date}.\n\n"
                "Можно сразу получить новый ключ по этим данным или написать имя другого мужчины."
            ),
            reply_markup=base.profile_partner_keyboard(),
        )
    else:
        await base._tracked_reply_text(
            update,
            context,
            (
                "Кого вы хотите понять лучше?\n\n"
                "Напишите имя или понятное обозначение: Андрей, муж, парень, партнёр.\n\n"
                "Имя нужно только для того, чтобы разбор звучал живо и лично."
            ),
            reply_markup=base.cancel_keyboard(),
        )

    return base.ASK_MAN_NAME


async def ask_man_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await base._remember_user(update)
    name = (update.effective_message.text or "").strip()
    if not name:
        await base._tracked_reply_text(update, context, "Напишите имя текстом. Например: Андрей")
        return base.ASK_MAN_NAME

    context.user_data["man_name"] = name[:60]
    await base._tracked_reply_text(
        update,
        context,
        (
            f"Теперь дата рождения {name}. Формат: 12.04.1993\n\n"
            "Точное время не обязательно. Сначала я покажу главный эмоциональный ключ: "
            "в какой атмосфере он легче идёт на контакт, что может его закрывать и какую фразу стоит попробовать."
        ),
        reply_markup=base.cancel_keyboard(),
    )
    return base.ASK_MAN_DATE


async def _build_man_report_from_date(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    name: str,
    birth_date_text: str,
) -> int:
    message = update.effective_message
    try:
        birth_date = base.parse_birth_date(birth_date_text)
    except ValueError as exc:
        await base._tracked_reply_text(update, context, str(exc))
        return base.ASK_MAN_DATE

    context.user_data["man_name"] = name[:60] or "мужчина"
    wait = await base._tracked_reply_text(
        update, context, "Собираю первый ключ: что открывает контакт, а что включает защиту…"
    )

    if message:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)

    try:
        chart = await asyncio.to_thread(base.calculate_partner_chart, birth_date)
        report = await asyncio.to_thread(
            base.build_partner_report,
            chart,
            context.user_data.get("man_name", "мужчина"),
        )
        base._save_report(context, base.LAST_MAN_REPORT, report)
        context.user_data["last_partner_report"] = report.to_dict()

        user_id = base._user_id(update)
        report_id = 0
        if user_id is not None:
            report_id = await asyncio.to_thread(base.get_store().add, user_id, report)
            context.user_data[base.LAST_MAN_REPORT_ID] = report_id
            await base._save_profile_fields(
                update,
                partner_name=context.user_data.get("man_name", ""),
                partner_birth_date=birth_date_text,
            )

        try:
            await wait.delete()
            base._forget_bot_message(context, wait)
        except Exception:
            pass

        await base._track_event(update, "man_free_report_generated")
        await base._send_long(
            update,
            context,
            format_free_preview(report),
            reply_markup=after_free_deep_keyboard(report_id),
        )
        await base._tracked_reply_text(
            update,
            context,
            (
                "Следующий шаг — не ещё больше текста о нём, а сравнение вас двоих.\n\n"
                "Добавьте свою дату, чтобы увидеть, что помогает каждому оставаться в контакте, "
                "где вы можете ждать друг от друга разного и какой небольшой шаг может учесть обоих."
            ),
            reply_markup=after_free_followup_keyboard(),
        )
    except Exception:
        base.logger.exception("Failed to build man report")
        error_text = "Не получилось собрать разбор. Проверьте дату в формате 12.04.1993 и попробуйте ещё раз."
        try:
            await wait.edit_text(error_text)
        except Exception:
            await base._tracked_reply_text(update, context, error_text)

    return ConversationHandler.END


async def start_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()

    await base._remember_user(update)
    await base._track_event(update, "self_flow_started")
    await base._set_chat_menu_button(update, context)

    if await base._load_latest_man_report(update, context) is None:
        await base._tracked_reply_text(update, context, base._state_lost_text(), reply_markup=menu())
        return ConversationHandler.END

    profile_data = await base._get_profile(update)
    self_name = profile_data.get("self_name", "").strip()
    self_birth_date = profile_data.get("self_birth_date", "").strip()

    if self_name and self_birth_date:
        await base._tracked_reply_text(
            update,
            context,
            (
                f"Ваши данные уже сохранены: {self_name}, {self_birth_date}.\n\n"
                "Используем их, чтобы сравнить ваши эмоциональные ритмы, или укажите другие данные."
            ),
            reply_markup=base.profile_self_keyboard(),
        )
    else:
        await base._tracked_reply_text(
            update,
            context,
            (
                "💞 Теперь добавим вас.\n\n"
                "Бот сравнит два равноправных ритма: что помогает ему оставаться в контакте, "
                "что помогает вам чувствовать тепло и ясность, и где вы можете ожидать друг от друга разного.\n\n"
                "Как назвать вас в разборе? Например: я, Анна, любимая."
            ),
            reply_markup=base.cancel_keyboard(),
        )

    return base.ASK_WOMAN_NAME


async def ask_woman_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await base._remember_user(update)
    name = (update.effective_message.text or "").strip()
    if not name:
        await base._tracked_reply_text(update, context, "Напишите имя текстом. Например: Анна")
        return base.ASK_WOMAN_NAME

    context.user_data["woman_name"] = name[:60]
    await base._tracked_reply_text(
        update,
        context,
        (
            "Теперь ваша дата рождения. Формат: 12.04.1993\n\n"
            "После этого вы увидите три вещи: где вам легко друг с другом, "
            "где нужны разные условия и какой конкретный мост можно попробовать уже сейчас."
        ),
        reply_markup=base.cancel_keyboard(),
    )
    return base.ASK_WOMAN_DATE


# Подменяем только продуктовый слой. Расчёты, хранение, оплаты и остальная
# инфраструктура остаются в проверенном основном модуле.
base.WELCOME_TEXT = WELCOME_TEXT
base.menu = menu
base.welcome_menu = welcome_menu
base.after_free_deep_keyboard = after_free_deep_keyboard
base.after_free_followup_keyboard = after_free_followup_keyboard
base.read_menu_keyboard = read_menu_keyboard
base.format_free_preview = format_free_preview
base.start_man = start_man
base.ask_man_date = ask_man_date
base._build_man_report_from_date = _build_man_report_from_date
base.start_self = start_self
base.ask_woman_date = ask_woman_date


def main() -> None:
    base.logger.info("BOT_BOOT: Python %s on %s", platform.python_version(), platform.platform())
    base.logger.info("BOT_BOOT: %s", base.settings.diagnostic_summary())
    base.logger.info("BOT_BOOT: starting sales-focused partner flow")
    base.start_webapp_server()
    base.build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
