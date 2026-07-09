from __future__ import annotations

import asyncio
import logging
from typing import Any

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    PreCheckoutQueryHandler,
    filters,
)

from app.astro.calculator import calculate_partner_chart, parse_birth_date
from app.astro.product_blocks import (
    format_couple_full_report,
    format_couple_moon_bridge,
    format_couple_portraits,
    format_jupiter_detail,
    format_mars_detail,
    format_mercury_detail,
    format_moon_detail,
    format_venus_detail,
)
from app.astro.report import PartnerReport, build_partner_report, format_free_preview
from app.config import settings
from app.payments import CURRENCY_STARS, PROVIDER_TOKEN_STARS, get_product, make_payload, parse_payload
from app.relationship_practice import (
    format_daily_connection_card,
    format_star_goal,
    get_daily_connection_card,
)
from app.services.openai_client import build_partner_message_with_ai
from app.storage import ReportsStore, format_history
from app.webapp import start_webapp_server

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ASK_MAN_NAME, ASK_MAN_DATE, ASK_WOMAN_NAME, ASK_WOMAN_DATE = range(4)
LAST_MAN_REPORT = "last_man_report"
LAST_WOMAN_REPORT = "last_woman_report"
LAST_MAN_REPORT_ID = "last_man_report_id"
ACTIVE_BOT_MESSAGE_IDS = "active_bot_message_ids"
_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path, settings.database_url)
    return _store


def webapp_info() -> WebAppInfo:
    return WebAppInfo(url=settings.webapp_url)


def webapp_menu_button() -> MenuButtonWebApp:
    return MenuButtonWebApp(text="Мои данные", web_app=webapp_info())


def profile_button() -> InlineKeyboardButton:
    return InlineKeyboardButton("👤 Мои данные", web_app=webapp_info())


def menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Начать разбор пары", callback_data="start_man")],
            [InlineKeyboardButton("🔑 Ключ на сегодня", callback_data="daily_key")],
            [InlineKeyboardButton("⭐️ Звёздная цель дня", callback_data="star_goal")],
            [profile_button()],
            [InlineKeyboardButton("🗂 История", callback_data="history")],
        ]
    )


def cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Отмена", callback_data="cancel")]])


def profile_partner_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Использовать партнёра из профиля",
                    callback_data="profile:use_partner",
                )
            ],
            [InlineKeyboardButton("Отмена", callback_data="cancel")],
        ]
    )


def profile_self_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "✅ Использовать мои данные из профиля",
                    callback_data="profile:use_self",
                )
            ],
            [InlineKeyboardButton("Отмена", callback_data="cancel")],
        ]
    )


def profile_only_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ В меню", callback_data="cancel")]])


def after_free_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Добавить себя и увидеть мост", callback_data="add_me")],
            [InlineKeyboardButton("💞 Новый разбор", callback_data="start_man")],
        ]
    )


def after_bridge_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("1️⃣ Луна: где ему спокойно", callback_data="p:moon")],
            [InlineKeyboardButton("2️⃣ Венера: что включает тепло", callback_data="p:venus")],
            [InlineKeyboardButton("3️⃣ Меркурий: как договориться", callback_data="p:mercury")],
            [InlineKeyboardButton("4️⃣ Марс: как поддержать действие", callback_data="p:mars")],
            [InlineKeyboardButton("5️⃣ Юпитер: куда расти вместе", callback_data="p:jupiter")],
            [InlineKeyboardButton("🔓 Premium: карта гармонии пары", callback_data="p:full")],
            [InlineKeyboardButton("👤 Premium: портреты в отношениях", callback_data="p:portrait")],
            [InlineKeyboardButton("✍️ Premium: что написать", callback_data="message")],
            [InlineKeyboardButton("💞 Новый разбор", callback_data="start_man")],
        ]
    )


def premium_paywall_text(product_key: str) -> str:
    if product_key == "message":
        return """
✍️ Premium-сообщение

Вы уже знаете эмоциональный мост. Следующий шаг — не ещё один абзац теории, а готовые формулировки, которые можно отправить без давления.

Внутри:
• 3 мягких варианта сообщения под его Луну;
• тональность по Меркурию — чтобы вас легче услышали;
• короткая подсказка, чего лучше не писать сейчас.

Подходит, когда хочется сделать шаг, но не хочется звучать навязчиво.
""".strip()
    return """
🔓 Premium-карта пары

Бесплатная часть показывает главный ключ. Premium собирает его в понятную цепочку действий: где человеку спокойно, что включает тепло, как говорить, как поддерживать движение и куда паре расти.

Внутри:
• полный разбор Луны, Венеры, Меркурия, Марса и Юпитера;
• портреты обоих в отношениях;
• карта гармонии пары без “процентов совместимости”;
• практичный порядок чтения — от эмоций к разговору и следующему шагу.

Это не гадание “да/нет”, а карта поведения, которую можно применить в переписке и встречах.
""".strip()


def premium_keyboard(product_key: str) -> InlineKeyboardMarkup:
    product = get_product(product_key)
    price = f"{product.stars} ⭐️" if product else "⭐️"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(f"Оплатить {price}", callback_data=f"premium:buy:{product_key}")],
            [InlineKeyboardButton("Сначала посмотреть блоки", callback_data="p:moon")],
            [InlineKeyboardButton("⬅️ Назад к карте", callback_data="premium:back")],
        ]
    )


def _user_id(update: Update) -> int | None:
    user = update.effective_user
    return user.id if user else None


def _is_authorized(update: Update) -> bool:
    if not settings.authorized_telegram_ids:
        return True
    user_id = _user_id(update)
    return bool(user_id and user_id in settings.authorized_telegram_ids)


async def _set_global_menu_button(application: Application) -> None:
    try:
        await application.bot.set_chat_menu_button(menu_button=webapp_menu_button())
        logger.info("WEBAPP_MENU_BUTTON: default menu button set to %s", settings.webapp_url)
    except Exception:
        logger.exception("WEBAPP_MENU_BUTTON_FAILED")


async def _set_chat_menu_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    try:
        await context.bot.set_chat_menu_button(chat_id=chat.id, menu_button=webapp_menu_button())
    except Exception:
        logger.exception("WEBAPP_CHAT_MENU_BUTTON_FAILED: chat_id=%s", chat.id)


async def _remember_user(update: Update) -> None:
    user_id = _user_id(update)
    if user_id is not None:
        await asyncio.to_thread(get_store().register_user, user_id)


async def _track_event(update: Update, event_name: str, **properties: Any) -> None:
    user_id = _user_id(update)
    safe_properties = {key: value for key, value in properties.items() if value is not None}
    try:
        await asyncio.to_thread(get_store().track_event, user_id, event_name, safe_properties)
    except Exception:
        logger.exception("ANALYTICS_EVENT_FAILED: event=%s user_id=%s", event_name, user_id)


async def _get_profile(update: Update) -> dict[str, str]:
    user_id = _user_id(update)
    if user_id is None:
        return {
            "self_name": "",
            "self_birth_date": "",
            "partner_name": "",
            "partner_birth_date": "",
        }
    return await asyncio.to_thread(get_store().get_profile, user_id)


async def _save_profile_fields(update: Update, **fields: str) -> None:
    user_id = _user_id(update)
    if user_id is None:
        return
    profile = await asyncio.to_thread(get_store().get_profile, user_id)
    profile.update({key: value for key, value in fields.items() if value})
    await asyncio.to_thread(get_store().save_profile, user_id, profile)


async def _deny(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("Доступ закрыт. Добавь Telegram ID в AUTHORIZED_TELEGRAM_IDS.")


def _clear_flow_state(context: ContextTypes.DEFAULT_TYPE) -> None:
    for key in (
        "man_name",
        "woman_name",
        LAST_MAN_REPORT,
        LAST_WOMAN_REPORT,
        "last_partner_report",
        LAST_MAN_REPORT_ID,
    ):
        context.user_data.pop(key, None)


def _active_bot_message_ids(context: ContextTypes.DEFAULT_TYPE) -> list[int]:
    raw = context.user_data.get(ACTIVE_BOT_MESSAGE_IDS)
    if not isinstance(raw, list):
        return []
    result: list[int] = []
    for item in raw:
        if isinstance(item, int) and item not in result:
            result.append(item)
    return result


def _remember_bot_message(context: ContextTypes.DEFAULT_TYPE, message: Any) -> None:
    message_id = getattr(message, "message_id", None)
    if not isinstance(message_id, int):
        return
    ids = _active_bot_message_ids(context)
    if message_id not in ids:
        ids.append(message_id)
    context.user_data[ACTIVE_BOT_MESSAGE_IDS] = ids


def _forget_bot_message(context: ContextTypes.DEFAULT_TYPE, message: Any) -> None:
    message_id = getattr(message, "message_id", None)
    if not isinstance(message_id, int):
        return
    context.user_data[ACTIVE_BOT_MESSAGE_IDS] = [
        item for item in _active_bot_message_ids(context) if item != message_id
    ]


async def _clear_active_bot_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    if chat is None:
        return
    ids = _active_bot_message_ids(context)
    context.user_data[ACTIVE_BOT_MESSAGE_IDS] = []
    for message_id in reversed(ids):
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=message_id)
        except Exception:
            pass


async def _tracked_reply_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs: Any) -> Any:
    message = update.effective_message
    if not message:
        return None
    sent = await message.reply_text(text, **kwargs)
    _remember_bot_message(context, sent)
    return sent


def _state_lost_text() -> str:
    return (
        "Я не вижу активного шага разбора. Возможно, бот перезапустился после обновления или это старая кнопка. "
        "Начни заново через /start или нажми «Начать разбор пары»."
    )


def _save_report(context: ContextTypes.DEFAULT_TYPE, key: str, report: PartnerReport) -> None:
    context.user_data[key] = report.to_dict()


def _report_from_payload(payload: object) -> PartnerReport | None:
    if not isinstance(payload, dict):
        return None
    payload = {key: value for key, value in payload.items() if key != "_storage_report_id"}
    try:
        return PartnerReport(**payload)
    except TypeError:
        return None


def _load_report(context: ContextTypes.DEFAULT_TYPE, key: str) -> PartnerReport | None:
    return _report_from_payload(context.user_data.get(key))


async def _load_latest_man_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> PartnerReport | None:
    report = _load_report(context, LAST_MAN_REPORT)
    if report is not None:
        return report
    user_id = _user_id(update)
    if user_id is None:
        return None
    payload = await asyncio.to_thread(get_store().latest_report_payload, user_id)
    report = _report_from_payload(payload)
    if report is not None:
        _save_report(context, LAST_MAN_REPORT, report)
        context.user_data["last_partner_report"] = report.to_dict()
        if isinstance(payload, dict) and payload.get("_storage_report_id"):
            context.user_data[LAST_MAN_REPORT_ID] = int(payload["_storage_report_id"])
    return report


async def _send_long(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs: Any) -> None:
    message = update.effective_message
    if not message:
        return
    rest = text.strip()
    parts: list[str] = []
    while len(rest) > 3900:
        cut = rest.rfind("\n", 0, 3900)
        if cut < 1000:
            cut = 3900
        parts.append(rest[:cut].strip())
        rest = rest[cut:].strip()
    if rest:
        parts.append(rest)
    for i, part in enumerate(parts):
        sent = await message.reply_text(
            part,
            disable_web_page_preview=True,
            **(kwargs if i == len(parts) - 1 else {}),
        )
        _remember_bot_message(context, sent)


async def _build_man_report_from_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE, name: str, birth_date_text: str
) -> int:
    message = update.effective_message
    try:
        birth_date = parse_birth_date(birth_date_text)
    except ValueError as exc:
        await _tracked_reply_text(update, context, str(exc))
        return ASK_MAN_DATE

    context.user_data["man_name"] = name[:60] or "мужчина"
    wait = await _tracked_reply_text(update, context, "Считаю его эмоциональный язык…")
    if message:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        chart = await asyncio.to_thread(calculate_partner_chart, birth_date)
        report = await asyncio.to_thread(build_partner_report, chart, context.user_data.get("man_name", "мужчина"))
        _save_report(context, LAST_MAN_REPORT, report)
        context.user_data["last_partner_report"] = report.to_dict()
        user_id = _user_id(update)
        if user_id is not None:
            report_id = await asyncio.to_thread(get_store().add, user_id, report)
            context.user_data[LAST_MAN_REPORT_ID] = report_id
            await _save_profile_fields(
                update,
                partner_name=context.user_data.get("man_name", ""),
                partner_birth_date=birth_date_text,
            )
        try:
            await wait.delete()
            _forget_bot_message(context, wait)
        except Exception:
            pass
        text = (
            f"{format_free_preview(report)}\n\n"
            "💞 Хотите увидеть ваш общий эмоциональный мост?\n"
            "Добавьте вашу дату рождения — я покажу, где спокойнее ему, где хорошо вам, "
            "и какой ритм помогает быть ближе без давления."
        )
        await _track_event(update, "man_free_report_generated")
        await _send_long(update, context, text, reply_markup=after_free_keyboard())
    except Exception:
        logger.exception("Failed to build man report")
        try:
            await wait.edit_text("Не получилось посчитать. Проверь дату в формате 12.04.1993 и попробуй ещё раз.")
        except Exception:
            await _tracked_reply_text(
                update,
                context,
                "Не получилось посчитать. Проверь дату в формате 12.04.1993 и попробуй ещё раз.",
            )
    return ConversationHandler.END


async def _build_bridge_from_date(
    update: Update, context: ContextTypes.DEFAULT_TYPE, name: str, birth_date_text: str
) -> int:
    man_report = await _load_latest_man_report(update, context)
    if man_report is None:
        await _tracked_reply_text(update, context, _state_lost_text(), reply_markup=menu())
        return ConversationHandler.END
    message = update.effective_message
    try:
        birth_date = parse_birth_date(birth_date_text)
    except ValueError as exc:
        await _tracked_reply_text(update, context, str(exc))
        return ASK_WOMAN_DATE
    context.user_data["woman_name"] = name[:60] or "вы"
    wait = await _tracked_reply_text(update, context, "Сравниваю ваши эмоциональные языки…")
    if message:
        await context.bot.send_chat_action(chat_id=message.chat_id, action=ChatAction.TYPING)
    try:
        chart = await asyncio.to_thread(calculate_partner_chart, birth_date)
        woman_report = await asyncio.to_thread(build_partner_report, chart, context.user_data.get("woman_name", "вы"))
        _save_report(context, LAST_WOMAN_REPORT, woman_report)
        await _save_profile_fields(
            update,
            self_name=context.user_data.get("woman_name", ""),
            self_birth_date=birth_date_text,
        )
        try:
            await wait.delete()
            _forget_bot_message(context, wait)
        except Exception:
            pass
        await _track_event(update, "couple_bridge_generated")
        await _send_long(
            update,
            context,
            format_couple_moon_bridge(man_report, woman_report),
            reply_markup=after_bridge_keyboard(),
        )
    except Exception:
        logger.exception("Failed to build bridge")
        try:
            await wait.edit_text("Не получилось сравнить Луны. Проверь дату и попробуй ещё раз.")
        except Exception:
            await _tracked_reply_text(
                update,
                context,
                "Не получилось сравнить Луны. Проверь дату и попробуй ещё раз.",
            )
    return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    await _remember_user(update)
    await _set_chat_menu_button(update, context)
    _clear_flow_state(context)
    await _track_event(update, "menu_opened", source="start")
    text = (
        "💞 Карта гармонии пары\n\n"
        "За 1 минуту покажу не «подходит / не подходит», а понятный следующий шаг: "
        "где мужчине спокойнее, где вам теплее и как говорить без давления.\n\n"
        "Как это работает:\n"
        "1. Введите имя и дату рождения мужчины.\n"
        "2. Получите бесплатный ключ: его эмоциональный язык и первый мягкий шаг.\n"
        "3. Добавьте свою дату — увидите ваш эмоциональный мост и готовую фразу для сообщения.\n\n"
        "Если сомневаетесь — начните с бесплатного ключа. Данные можно сохранить в «Мои данные», "
        "чтобы не вводить их каждый раз."
    )
    await update.effective_message.reply_text(text, reply_markup=menu())
    return ConversationHandler.END


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await _set_chat_menu_button(update, context)
    await update.effective_message.reply_text(
        "👤 Нижняя кнопка «Мои данные» открывает мини-приложение. Там можно сохранить свои данные и данные партнёра, чтобы бот подтягивал их в разбор.",
        reply_markup=profile_only_keyboard(),
    )


async def daily_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await _track_event(update, "daily_key_opened")
    card = get_daily_connection_card(_user_id(update), settings.app_timezone)
    await update.effective_message.reply_text(format_daily_connection_card(card), reply_markup=menu())


async def star_goal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await _track_event(update, "star_goal_opened")
    await update.effective_message.reply_text(format_star_goal(settings.app_timezone), reply_markup=menu())


async def start_man(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return ConversationHandler.END
    await _remember_user(update)
    await _track_event(update, "partner_flow_started")
    await _set_chat_menu_button(update, context)
    await _clear_active_bot_messages(update, context)
    if update.callback_query:
        try:
            await update.callback_query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
    _clear_flow_state(context)
    profile_data = await _get_profile(update)
    partner_name = profile_data.get("partner_name", "").strip()
    partner_birth_date = profile_data.get("partner_birth_date", "").strip()
    if partner_name and partner_birth_date:
        await _tracked_reply_text(
            update,
            context,
            f"В профиле сохранён партнёр: {partner_name}, {partner_birth_date}.\n\nМожно использовать эти данные или написать новое имя мужчины.",
            reply_markup=profile_partner_keyboard(),
        )
    else:
        await _tracked_reply_text(
            update,
            context,
            "Как зовут мужчину? Например: Андрей, муж, парень, партнёр.\n\nДанные можно заранее сохранить через нижнюю кнопку «Мои данные», чтобы потом не вводить заново.",
            reply_markup=cancel_keyboard(),
        )
    return ASK_MAN_NAME


async def use_partner_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    profile_data = await _get_profile(update)
    name = profile_data.get("partner_name", "").strip()
    birth_date = profile_data.get("partner_birth_date", "").strip()
    if not name or not birth_date:
        await _tracked_reply_text(
            update,
            context,
            "В профиле пока нет полных данных партнёра. Откройте «Мои данные» и заполните имя и дату рождения.",
            reply_markup=profile_only_keyboard(),
        )
        return ConversationHandler.END
    return await _build_man_report_from_date(update, context, name, birth_date)


async def ask_man_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _remember_user(update)
    name = (update.effective_message.text or "").strip()
    if not name:
        await _tracked_reply_text(update, context, "Напиши имя текстом. Например: Андрей")
        return ASK_MAN_NAME
    context.user_data["man_name"] = name[:60]
    await _tracked_reply_text(
        update,
        context,
        "Дата рождения мужчины. Формат: 12.04.1993",
        reply_markup=cancel_keyboard(),
    )
    return ASK_MAN_DATE


async def build_man_free(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _remember_user(update)
    return await _build_man_report_from_date(
        update,
        context,
        context.user_data.get("man_name", "мужчина"),
        (update.effective_message.text or "").strip(),
    )


async def start_self(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    await _track_event(update, "self_flow_started")
    await _set_chat_menu_button(update, context)
    if await _load_latest_man_report(update, context) is None:
        await _tracked_reply_text(update, context, _state_lost_text(), reply_markup=menu())
        return ConversationHandler.END
    profile_data = await _get_profile(update)
    self_name = profile_data.get("self_name", "").strip()
    self_birth_date = profile_data.get("self_birth_date", "").strip()
    if self_name and self_birth_date:
        await _tracked_reply_text(
            update,
            context,
            f"В профиле сохранены ваши данные: {self_name}, {self_birth_date}.\n\nМожно использовать их или написать другое имя для разбора.",
            reply_markup=profile_self_keyboard(),
        )
    else:
        await _tracked_reply_text(
            update,
            context,
            "Как вас назвать в разборе? Например: я, Анна, любимая.",
            reply_markup=cancel_keyboard(),
        )
    return ASK_WOMAN_NAME


async def use_self_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    profile_data = await _get_profile(update)
    name = profile_data.get("self_name", "").strip()
    birth_date = profile_data.get("self_birth_date", "").strip()
    if not name or not birth_date:
        await _tracked_reply_text(
            update,
            context,
            "В профиле пока нет ваших полных данных. Откройте «Мои данные» и заполните имя и дату рождения.",
            reply_markup=profile_only_keyboard(),
        )
        return ConversationHandler.END
    return await _build_bridge_from_date(update, context, name, birth_date)


async def ask_woman_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _remember_user(update)
    name = (update.effective_message.text or "").strip()
    if not name:
        await _tracked_reply_text(update, context, "Напиши имя текстом. Например: Анна")
        return ASK_WOMAN_NAME
    context.user_data["woman_name"] = name[:60]
    await _tracked_reply_text(
        update,
        context,
        "Теперь ваша дата рождения. Формат: 12.04.1993",
        reply_markup=cancel_keyboard(),
    )
    return ASK_WOMAN_DATE


async def build_bridge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await _remember_user(update)
    return await _build_bridge_from_date(
        update,
        context,
        context.user_data.get("woman_name", "вы"),
        (update.effective_message.text or "").strip(),
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    _clear_flow_state(context)
    await _tracked_reply_text(
        update,
        context,
        "Ок, остановил. Начать заново можно через /start.",
        reply_markup=menu(),
    )
    return ConversationHandler.END


async def history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    user_id = _user_id(update)
    if user_id is None:
        return
    await update.effective_message.reply_text(
        format_history(get_store().recent(user_id, limit=10)), reply_markup=menu()
    )


async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    code = (update.callback_query.data or "").replace("p:", "") if update.callback_query else ""
    await _track_event(update, "product_block_opened", block=code)
    man_report = await _load_latest_man_report(update, context)
    if man_report is None:
        await _tracked_reply_text(update, context, _state_lost_text(), reply_markup=menu())
        return
    woman_report = _load_report(context, LAST_WOMAN_REPORT)
    if woman_report is None:
        await _tracked_reply_text(
            update,
            context,
            "Чтобы открыть глубокие блоки и карту гармонии пары, сначала добавьте вашу дату рождения.",
            reply_markup=after_free_keyboard(),
        )
        return
    report_id = _current_report_id(context)
    if code in {"full", "portrait"} and not await _has_premium_access(update, context, "details", report_id):
        await _track_event(update, "premium_gate_hit", product_key="details", block=code, report_id=report_id)
        await _tracked_reply_text(update, context, premium_paywall_text("details"), reply_markup=premium_keyboard("details"))
        return
    if code == "full":
        await _send_long(
            update,
            context,
            format_couple_full_report(man_report, woman_report),
            reply_markup=after_bridge_keyboard(),
        )
        return
    if code == "portrait":
        await _send_long(
            update,
            context,
            format_couple_portraits(man_report, woman_report),
            reply_markup=after_bridge_keyboard(),
        )
        return
    formatters = {
        "moon": format_moon_detail,
        "venus": format_venus_detail,
        "mercury": format_mercury_detail,
        "mars": format_mars_detail,
        "jupiter": format_jupiter_detail,
    }
    formatter = formatters.get(code)
    if formatter is None:
        await _tracked_reply_text(
            update,
            context,
            "Этот блок пока не найден.",
            reply_markup=after_bridge_keyboard(),
        )
        return
    await _send_long(update, context, formatter(man_report), reply_markup=after_bridge_keyboard())


def _current_report_id(context: ContextTypes.DEFAULT_TYPE) -> int:
    raw = context.user_data.get(LAST_MAN_REPORT_ID)
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


async def _has_premium_access(
    update: Update, context: ContextTypes.DEFAULT_TYPE, product_key: str, report_id: int
) -> bool:
    user_id = _user_id(update)
    if user_id is None or report_id <= 0:
        return False
    return await asyncio.to_thread(get_store().has_entitlement, user_id, product_key, report_id)


async def premium_offer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    data = update.callback_query.data if update.callback_query else ""
    product_key = (data or "").replace("premium:", "")
    if product_key == "back":
        await _tracked_reply_text(update, context, "Вернул к карте пары.", reply_markup=after_bridge_keyboard())
        return
    if product_key not in {"details", "message"}:
        product_key = "details"
    await _track_event(update, "premium_paywall_viewed", product_key=product_key)
    await _tracked_reply_text(update, context, premium_paywall_text(product_key), reply_markup=premium_keyboard(product_key))


async def premium_buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    await _remember_user(update)
    product_key = (query.data or "").replace("premium:buy:", "") if query else ""
    product = get_product(product_key)
    report_id = _current_report_id(context)
    if product is None or report_id <= 0:
        await _tracked_reply_text(
            update,
            context,
            "Сначала соберите разбор пары — тогда я привяжу Premium к конкретной карте.",
            reply_markup=after_free_keyboard(),
        )
        return
    await _track_event(update, "premium_invoice_opened", product_key=product_key, report_id=report_id)
    message = update.effective_message
    if not message:
        return
    await context.bot.send_invoice(
        chat_id=message.chat_id,
        title=product.title,
        description=product.description,
        payload=make_payload(product_key, report_id),
        provider_token=PROVIDER_TOKEN_STARS,
        currency=CURRENCY_STARS,
        prices=[product.price],
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return
    parsed = parse_payload(query.invoice_payload)
    if parsed is None:
        await query.answer(ok=False, error_message="Не получилось распознать продукт. Попробуйте открыть оплату заново.")
        return
    await query.answer(ok=True)
    product_key, report_id = parsed
    await _track_event(update, "premium_precheckout_approved", product_key=product_key, report_id=report_id)


async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    payment = update.effective_message.successful_payment if update.effective_message else None
    if payment is None:
        return
    parsed = parse_payload(payment.invoice_payload)
    if parsed is None:
        await _tracked_reply_text(update, context, "Оплата прошла, но продукт не распознан. Напишите администратору.")
        return
    product_key, report_id = parsed
    user_id = _user_id(update)
    if user_id is not None:
        await asyncio.to_thread(
            get_store().grant_entitlement,
            user_id,
            product_key,
            report_id,
            payment.telegram_payment_charge_id,
        )
    await _track_event(update, "premium_payment_succeeded", product_key=product_key, report_id=report_id)
    await _tracked_reply_text(
        update,
        context,
        "Готово — Premium открыт для этой карты пары. Выберите, что посмотреть первым.",
        reply_markup=after_bridge_keyboard(),
    )


async def message_hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    await _remember_user(update)
    await _track_event(update, "message_hint_requested")
    report = await _load_latest_man_report(update, context)
    if report is None:
        await _tracked_reply_text(update, context, _state_lost_text(), reply_markup=menu())
        return
    if _load_report(context, LAST_WOMAN_REPORT) is None:
        await _tracked_reply_text(
            update,
            context,
            "Сначала добавьте вашу дату рождения и посмотрите эмоциональный мост. После этого я соберу варианты сообщения уже в контексте пары.",
            reply_markup=after_free_keyboard(),
        )
        return
    report_id = _current_report_id(context)
    if not await _has_premium_access(update, context, "message", report_id):
        await _track_event(update, "premium_gate_hit", product_key="message", block="message", report_id=report_id)
        await _tracked_reply_text(update, context, premium_paywall_text("message"), reply_markup=premium_keyboard("message"))
        return
    wait = await _tracked_reply_text(update, context, "Собираю мягкие варианты сообщения…")
    text = await asyncio.to_thread(build_partner_message_with_ai, report)
    try:
        await wait.delete()
        _forget_bot_message(context, wait)
    except Exception:
        pass
    await _tracked_reply_text(update, context, text, reply_markup=after_bridge_keyboard())


async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    text = (update.effective_message.text or "").strip()
    try:
        parse_birth_date(text)
        await update.effective_message.reply_text(
            "Похоже, ты отправил дату, но я сейчас не вижу активного шага разбора. "
            "После обновления бот мог потерять состояние. Начни заново через /start.",
            reply_markup=menu(),
        )
        return
    except ValueError:
        pass
    await update.effective_message.reply_text(
        "Я сейчас не жду обычный текст. Начни разбор через /start и нажми «Начать разбор пары». "
        "Если бот только что обновлялся, старый шаг мог сброситься. Да, память у серверов иногда как у золотой рыбки после кофе.",
        reply_markup=menu(),
    )


def build_application() -> Application:
    settings.validate_runtime()
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(_set_global_menu_button).build()
    reset_handlers = [
        CommandHandler("start", start),
        CommandHandler("menu", start),
        CommandHandler("reset", start),
    ]
    man_flow = ConversationHandler(
        entry_points=[
            *reset_handlers,
            CommandHandler("man", start_man),
            CommandHandler("partner", start_man),
            CallbackQueryHandler(start_man, pattern=r"^start_man$"),
        ],
        states={
            ASK_MAN_NAME: [
                CallbackQueryHandler(use_partner_profile, pattern=r"^profile:use_partner$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_man_date),
            ],
            ASK_MAN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, build_man_free)],
        },
        fallbacks=[
            *reset_handlers,
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )
    self_flow = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_self, pattern=r"^add_me$")],
        states={
            ASK_WOMAN_NAME: [
                CallbackQueryHandler(use_self_profile, pattern=r"^profile:use_self$"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ask_woman_date),
            ],
            ASK_WOMAN_DATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, build_bridge)],
        },
        fallbacks=[
            *reset_handlers,
            CallbackQueryHandler(cancel, pattern=r"^cancel$"),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(man_flow)
    app.add_handler(self_flow)
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("daily", daily_key))
    app.add_handler(CommandHandler("stars", star_goal))
    app.add_handler(CallbackQueryHandler(history, pattern=r"^history$"))
    app.add_handler(CallbackQueryHandler(daily_key, pattern=r"^daily_key$"))
    app.add_handler(CallbackQueryHandler(star_goal, pattern=r"^star_goal$"))
    app.add_handler(CallbackQueryHandler(premium_offer, pattern=r"^premium:(details|message|back)$"))
    app.add_handler(CallbackQueryHandler(premium_buy, pattern=r"^premium:buy:(details|message)$"))
    app.add_handler(CallbackQueryHandler(product_detail, pattern=r"^p:(moon|venus|mercury|mars|jupiter|portrait|full)$"))
    app.add_handler(CallbackQueryHandler(message_hint, pattern=r"^message$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))
    return app


def main() -> None:
    logger.info("BOT_BOOT: starting couple harmony flow")
    start_webapp_server()
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
