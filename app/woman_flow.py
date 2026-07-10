from __future__ import annotations

import asyncio
import logging
import platform
from datetime import datetime, time, timedelta
from typing import Any
from urllib.parse import urlencode
from zoneinfo import ZoneInfo

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonWebApp,
    Update,
    WebAppInfo,
)
from telegram.constants import ChatAction
from telegram.error import TelegramError
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
    format_couple_moon_bridge_short_card,
    format_couple_portraits_short_card,
    format_planet_short_card,
)
from app.astro.report import PartnerReport, build_partner_report, format_free_preview, format_message_guidance
from app.config import settings
from app.payments import (
    CURRENCY_STARS,
    PROVIDER_TOKEN_STARS,
    create_yookassa_payment,
    get_product,
    get_yookassa_payment,
    make_payload,
    parse_payload,
)
from app.relationship_practice import (
    format_daily_connection_card,
    format_star_goal,
    get_daily_connection_card,
)
from app.storage import ReportsStore, format_history
from app.webapp import start_webapp_server

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

ASK_MAN_NAME, ASK_MAN_DATE, ASK_WOMAN_NAME, ASK_WOMAN_DATE = range(4)
LAST_MAN_REPORT = "last_man_report"
LAST_WOMAN_REPORT = "last_woman_report"
LAST_MAN_REPORT_ID = "last_man_report_id"
ACTIVE_BOT_MESSAGE_IDS = "active_bot_message_ids"
PENDING_YOOKASSA_PAYMENT = "pending_yookassa_payment"
DAILY_KEY_HOUR = 8
DAILY_KEY_MINUTE = 0
MERCURY_BROADCAST_KEY = "mercury_retrograde_opportunity_2026_07"

PAID_PLANET_PRODUCTS = {
    "venus": "planet_venus",
    "mercury": "planet_mercury",
    "mars": "planet_mars",
    "jupiter": "planet_jupiter",
}
PLANET_PAYWALL_COPY = {
    "planet_venus": ("💗 Венера", "женская Венера"),
    "planet_mercury": ("🗣 Меркурий", "ваш Меркурий"),
    "planet_mars": ("🔥 Марс", "ваш Марс"),
    "planet_jupiter": ("🪐 Юпитер", "ваш Юпитер"),
}

MERCURY_BROADCAST_TEXT = """
🗣 Ретроградный Меркурий — окно возможностей

Сейчас хороший период не пугаться, а прояснять: детали, переписку, договорённости и то, что в отношениях осталось недосказанным.

Меркурий помогает понять, как человек мыслит, слышит, объясняет и договаривается.

В отношениях это шанс уточнить:
— что каждый имел в виду;
— где вас могли услышать не так;
— о чём пора поговорить спокойнее;
— какой маленький шаг вернёт ясность.

Откройте разбор и посмотрите блок:
🗣 Меркурий — как человек мыслит и договаривается

Иногда новый уровень начинается не с громкого решения, а с честного и ясного разговора.
""".strip()

DAILY_KEY_THEMES = [
    ("Луна", "эмоциональную безопасность", "сначала признать чувство, потом предлагать решение"),
    ("Венера", "тёплое притяжение", "добавить конкретный комплимент бережно"),
    ("Меркурий", "ясный разговор", "задать один прямой вопрос и не спорить с ответом"),
    ("Марс", "уважение к инициативе", "дать пространство для действия, а не контролировать каждый шаг"),
    ("Солнце", "уважение к его роли", "заметить, где он уже старается"),
    ("Сатурн", "надёжность", "договориться о маленьком понятном шаге"),
    ("Юпитер", "веру в лучшее", "говорить через возможность, а не через претензию"),
]

DAILY_KEY_TONES = [
    "мягко",
    "коротко",
    "без проверки и допроса",
    "с теплом, но с границами",
    "через благодарность",
    "спокойно и конкретно",
    "без намёков",
]

WELCOME_TEXT = """
💞 Инструкция к вашему мужчине.

📦 К каждому устройству прилагается инструкция.
💌 К мужчине, которого вы любите, почему-то нет.

✨ Мы решили это исправить.

📖 Перед использованием мужчины рекомендуется ознакомиться с инструкцией.

🗓️ Приложение помогает девушке понять мужчину по дате рождения: где ему эмоционально спокойно, как он проявляет чувства и как с ним говорить, чтобы обоим было хорошо, а дела шли в гору.

🤍 Это не проверка совместимости.
🧭 Это карта понимания: как создать процветающие отношения.
""".strip()

ABOUT_TEXT = """
Что делает бот:

1. Берёт дату рождения мужчины.
2. Считает Луну, Венеру, Меркурий и Марс через Swiss Ephemeris.
3. Сначала даёт короткий бесплатный ключ: эмоциональный язык и первый шаг.
4. Затем предлагает добавить ваши данные, увидеть мост пары, открыть планеты и Premium-карту.

Формат — как инструкция к человеку: легко улыбнуться, но сразу понятно, что попробовать в реальном разговоре.

Без синастрии, процентов любви и космического суда. Только практичное понимание человека и отношений.
""".strip()


_store: ReportsStore | None = None


def get_store() -> ReportsStore:
    global _store
    if _store is None:
        _store = ReportsStore(settings.reports_db_path, settings.database_url)
    return _store


def _app_timezone() -> ZoneInfo:
    try:
        return ZoneInfo(settings.app_timezone)
    except Exception:
        logger.warning("Invalid APP_TIMEZONE=%s; falling back to Europe/Moscow", settings.app_timezone)
        return ZoneInfo("Europe/Moscow")


def _daily_key_broadcast_key(now: datetime | None = None) -> str:
    tz = _app_timezone()
    local_now = now.astimezone(tz) if now else datetime.now(tz)
    return f"daily_partner_key_{local_now:%Y_%m_%d}"


def build_daily_partner_key_text(now: datetime | None = None) -> str:
    tz = _app_timezone()
    local_now = now.astimezone(tz) if now else datetime.now(tz)
    day_seed = local_now.toordinal()
    theme_name, focus, action = DAILY_KEY_THEMES[day_seed % len(DAILY_KEY_THEMES)]
    tone = DAILY_KEY_TONES[(day_seed // len(DAILY_KEY_THEMES)) % len(DAILY_KEY_TONES)]
    date_label = local_now.strftime("%d.%m.%Y")
    key_code = f"{theme_name[:1].upper()}-{day_seed % 97:02d}"

    return f"""
🔑 Ключ к мужчине на сегодня — {date_label}

Код дня: {key_code}
Планета-фокус: {theme_name}
Главная тема: {focus}

Как применить сегодня:
— действуй {tone};
— {action};
— выбери один маленький шаг, а не большой разговор на два часа.

Если хочешь точнее — сделай разбор пары: /partner
""".strip()


def _next_daily_key_run(now: datetime | None = None) -> datetime:
    tz = _app_timezone()
    local_now = now.astimezone(tz) if now else datetime.now(tz)
    run_at = datetime.combine(local_now.date(), time(DAILY_KEY_HOUR, DAILY_KEY_MINUTE), tzinfo=tz)
    if local_now >= run_at:
        run_at += timedelta(days=1)
    return run_at


def webapp_info() -> WebAppInfo:
    return WebAppInfo(url=settings.webapp_url)


def detail_webapp_info(block: str) -> WebAppInfo:
    base_url = settings.webapp_url.rstrip("/")
    if base_url.endswith("/webapp"):
        base_url = base_url[: -len("/webapp")]
    return WebAppInfo(url=f"{base_url}/webapp/detail?{urlencode({'block': block})}")


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


def after_free_deep_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🌙 Луна мужчины глубже", web_app=detail_webapp_info("moon_deep"))]]
    )


def after_free_followup_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💞 Добавить себя и увидеть мост", callback_data="add_me")],
            [InlineKeyboardButton("💞 Новый разбор", callback_data="start_man")],
        ]
    )


def after_free_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            *after_free_deep_keyboard().inline_keyboard,
            *after_free_followup_keyboard().inline_keyboard,
        ]
    )


def read_menu_keyboard() -> InlineKeyboardMarkup:
    """Menu shown inside the relationship reading after short detail cards."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("1️⃣ Венера: как включить его нежность", callback_data="p:venus")],
            [InlineKeyboardButton("2️⃣ Меркурий: слова, которые он слышит", callback_data="p:mercury")],
            [InlineKeyboardButton("3️⃣ Марс: как дать ему силу действовать", callback_data="p:mars")],
            [InlineKeyboardButton("4️⃣ Юпитер: куда вести вашу пару", callback_data="p:jupiter")],
            [InlineKeyboardButton("🔓 Premium: мощная карта гармонии", callback_data="p:full")],
            [InlineKeyboardButton("👤 Premium: глубокие портреты пары", callback_data="p:portrait")],
            [InlineKeyboardButton("✍️ Premium: сообщение с эффектом", callback_data="message")],
            [InlineKeyboardButton("💞 Новый разбор", callback_data="start_man")],
        ]
    )


def after_bridge_keyboard() -> InlineKeyboardMarkup:
    return read_menu_keyboard()


def detail_card_keyboard(block: str, locked: bool = False) -> InlineKeyboardMarkup:
    labels = {
        "moon": "🌙 Луна (глубже)",
        "moon_deep": "🌙 Луна мужчины глубже",
        "venus": "💗 Открыть подробную Венеру",
        "mercury": "🗣 Открыть подробный Меркурий",
        "mars": "🔥 Открыть подробный Марс",
        "jupiter": "🪐 Открыть подробный Юпитер",
        "portrait": "👤 Открыть подробные портреты",
        "full": "📖 Открыть расширенную карту",
        "bridge": "💞 Открыть полный эмоциональный мост",
    }
    if locked and block in PAID_PLANET_PRODUCTS:
        primary_button = InlineKeyboardButton(
            "🔓 Открыть за 50 ₽ · ваша планета бесплатно",
            callback_data=f"premium:planet:{block}",
        )
    else:
        primary_button = InlineKeyboardButton(
            labels.get(block, "✨ Открыть подробности"), web_app=detail_webapp_info(block)
        )
    return InlineKeyboardMarkup(
        [
            [primary_button],
            *read_menu_keyboard().inline_keyboard,
        ]
    )


def bridge_summary_keyboard() -> InlineKeyboardMarkup:
    """CTA shown on the bridge teaser; navigation is sent as a separate menu."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("💞 Открыть полный эмоциональный мост", web_app=detail_webapp_info("bridge"))]]
    )


async def _delete_callback_menu_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove the tapped inline menu before rendering the next content card."""
    query = update.callback_query
    if not query or not query.message:
        return
    try:
        await query.message.delete()
        _forget_bot_message(context, query.message)
    except Exception:
        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass


async def _send_bridge_teaser_with_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    await _send_long(update, context, text, reply_markup=bridge_summary_keyboard())
    await _tracked_reply_text(update, context, "📖 Меню разбора", reply_markup=read_menu_keyboard())


def premium_paywall_text(product_key: str) -> str:
    if product_key in PLANET_PAYWALL_COPY:
        planet_label, free_label = PLANET_PAYWALL_COPY[product_key]
        return f"""
{planet_label}: подробный блок пары

Откройте подробную планету мужчины за 50 ₽ — а {free_label} добавим бесплатно. Так разбор становится не односторонним: вы видите не только его сценарий, но и ваш естественный способ отвечать, говорить, сближаться и поддерживать контакт.

Внутри:
• его подробная планета: что включает, что закрывает и какой шаг работает мягче;
• ваша планета бесплатно — чтобы сравнить ритмы без отдельной оплаты;
• практичный мост для пары: как применить подсказку в переписке, разговоре или встрече;
• короткая формулировка без мистики и давления: что попробовать сегодня.

Формат аккуратный: одна планета — один понятный фокус за 50 ₽, без необходимости сразу покупать большой разбор.
""".strip()
    if product_key == "message":
        return """
✍️ Premium-сообщение с эффектом

Вы уже знаете эмоциональный мост. Теперь нужен не ещё один абзац теории, а сильный, бережный текст, который помогает начать разговор без давления и лишней тревоги.

Внутри:
• 3 готовых варианта сообщения под его эмоциональный ритм;
• тональность по Меркурию — чтобы фраза звучала естественно и вас было легче услышать;
• стоп-фраза: что лучше не писать сейчас, чтобы не закрыть диалог;
• понятный первый шаг, если хочется сблизиться, но не выглядеть навязчиво.

Это мини-сценарий для сообщения, которое может мягко сдвинуть контакт: меньше угадываний, больше ясности и уверенности.
""".strip()
    return """
🔓 Premium-карта пары: глубокий разбор

Бесплатная часть даёт главный ключ. Premium превращает его в мощную карту действий: как стать для него тихой гаванью, включать нежность, говорить словами, которые он слышит, поддерживать его силу и видеть следующий горизонт пары.

Внутри:
• полный разбор Луны, Венеры, Меркурия, Марса и Юпитера;
• глубокие портреты обоих в отношениях — сильные стороны, уязвимости и точки сближения;
• карта гармонии пары без “процентов совместимости”: не ярлык, а практичный маршрут;
• порядок чтения от эмоций к разговору и следующему шагу, чтобы сразу применить выводы в переписке и встречах.

Это не гадание “да/нет”, а персональная навигация по поведению пары: меньше хаоса, больше ясности, тепла и действий, которые могут реально усилить контакт.
""".strip()


def premium_keyboard(product_key: str) -> InlineKeyboardMarkup:
    product = get_product(product_key)
    if product and settings.yookassa_enabled:
        price = f"{product.rubles} ₽"
    else:
        price = f"{product.stars} ⭐️" if product else "⭐️"
    if product_key in PLANET_PAYWALL_COPY:
        buy_label = f"Открыть планету за {price} · ваша бесплатно"
        secondary_label = "Посмотреть бесплатные подсказки"
    else:
        buy_label = f"Получить Premium за {price}"
        secondary_label = "Сначала посмотреть блоки"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(buy_label, callback_data=f"premium:buy:{product_key}")],
            [InlineKeyboardButton(secondary_label, callback_data="p:moon")],
            [InlineKeyboardButton("📖 Меню", callback_data="premium:back")],
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


def _is_broadcast_admin(update: Update) -> bool:
    user_id = _user_id(update)
    admin_ids = settings.broadcast_admin_ids | settings.authorized_telegram_ids
    return bool(user_id and user_id in admin_ids)


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


async def _send_broadcast(
    application: Application,
    *,
    broadcast_key: str,
    text: str,
    log_prefix: str,
    force: bool = False,
) -> tuple[int, int, int, str]:
    store = get_store()
    if not force and await asyncio.to_thread(store.was_broadcast_sent, broadcast_key):
        return 0, 0, 0, "already_sent"

    user_ids = await asyncio.to_thread(store.all_user_ids)
    if not user_ids:
        return 0, 0, 0, "no_users"

    total = len(user_ids)
    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            await application.bot.send_message(
                chat_id=user_id,
                text=text,
                disable_web_page_preview=True,
                reply_markup=menu(),
            )
        except TelegramError as exc:
            failed += 1
            logger.warning("%s: failed user_id=%s error=%s", log_prefix, user_id, exc)
        else:
            success += 1
        await asyncio.sleep(0.05)

    if success > 0:
        await asyncio.to_thread(store.mark_broadcast_sent, broadcast_key, total, success, failed)
    return total, success, failed, "sent"


async def _send_mercury_broadcast(application: Application, *, force: bool = False) -> tuple[int, int, int, str]:
    return await _send_broadcast(
        application,
        broadcast_key=MERCURY_BROADCAST_KEY,
        text=MERCURY_BROADCAST_TEXT,
        log_prefix="MERCURY_BROADCAST",
        force=force,
    )


async def _send_daily_key_broadcast(
    application: Application, *, force: bool = False, now: datetime | None = None
) -> tuple[int, int, int, str]:
    return await _send_broadcast(
        application,
        broadcast_key=_daily_key_broadcast_key(now),
        text=build_daily_partner_key_text(now),
        log_prefix="DAILY_KEY_BROADCAST",
        force=force,
    )


async def _daily_key_scheduler(application: Application) -> None:
    while True:
        run_at = _next_daily_key_run()
        sleep_seconds = max(1.0, (run_at - datetime.now(run_at.tzinfo)).total_seconds())
        logger.info("DAILY_KEY_SCHEDULER: next_run=%s", run_at.isoformat(timespec="seconds"))
        await asyncio.sleep(sleep_seconds)
        try:
            total, success, failed, status = await _send_daily_key_broadcast(application, force=False)
            logger.info(
                "DAILY_KEY_SCHEDULED: status=%s total=%s success=%s failed=%s",
                status,
                total,
                success,
                failed,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("DAILY_KEY_SCHEDULED_FAILED")


async def _post_init(application: Application) -> None:
    await _set_global_menu_button(application)
    if datetime.now(_app_timezone()).time() >= time(DAILY_KEY_HOUR, DAILY_KEY_MINUTE):
        try:
            total, success, failed, status = await _send_daily_key_broadcast(application, force=False)
            logger.info(
                "DAILY_KEY_ON_BOOT: status=%s total=%s success=%s failed=%s",
                status,
                total,
                success,
                failed,
            )
        except Exception:
            logger.exception("DAILY_KEY_ON_BOOT_FAILED")

    application.create_task(_daily_key_scheduler(application), name="daily-key-scheduler")

    try:
        total, success, failed, status = await _send_mercury_broadcast(application, force=False)
        logger.info(
            "MERCURY_BROADCAST_ON_BOOT: status=%s total=%s success=%s failed=%s",
            status,
            total,
            success,
            failed,
        )
    except Exception:
        logger.exception("MERCURY_BROADCAST_ON_BOOT_FAILED")


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
        text = format_free_preview(report)
        await _track_event(update, "man_free_report_generated")
        await _send_long(update, context, text, reply_markup=after_free_deep_keyboard())
        await _tracked_reply_text(
            update,
            context,
            "👇 Добавьте свою дату для моста пары или начните новый разбор.",
            reply_markup=after_free_followup_keyboard(),
        )
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
        await _send_bridge_teaser_with_menu(
            update,
            context,
            format_couple_moon_bridge_short_card(man_report, woman_report),
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
    await update.effective_message.reply_text(WELCOME_TEXT, reply_markup=menu())
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


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _remember_user(update)
    user_id = _user_id(update)
    if user_id:
        await update.effective_message.reply_text(f"Твой Telegram ID: {user_id}")


async def about(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.callback_query:
        await update.callback_query.answer()
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await update.effective_message.reply_text(ABOUT_TEXT, reply_markup=menu())


async def today_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_authorized(update):
        await _deny(update)
        return
    await _remember_user(update)
    await _track_event(update, "today_key_opened")
    await update.effective_message.reply_text(build_daily_partner_key_text(), reply_markup=menu())


async def broadcast_daily_key(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_broadcast_admin(update):
        await update.effective_message.reply_text(
            "Команда рассылки доступна только админу. Добавь свой Telegram ID в BROADCAST_ADMIN_IDS или AUTHORIZED_TELEGRAM_IDS на Railway."
        )
        return
    await _remember_user(update)
    wait = await update.effective_message.reply_text("Запускаю рассылку ключа на сегодня…")
    total, success, failed, status = await _send_daily_key_broadcast(context.application, force=True)
    await wait.edit_text(
        f"Рассылка завершена.\n\nСтатус: {status}\nВсего: {total}\nОтправлено: {success}\nОшибок: {failed}"
    )


async def broadcast_mercury(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _is_broadcast_admin(update):
        await update.effective_message.reply_text(
            "Команда рассылки доступна только админу. Добавь свой Telegram ID в BROADCAST_ADMIN_IDS или AUTHORIZED_TELEGRAM_IDS на Railway."
        )
        return
    await _remember_user(update)
    wait = await update.effective_message.reply_text("Запускаю рассылку про ретроградный Меркурий…")
    total, success, failed, status = await _send_mercury_broadcast(context.application, force=True)
    await wait.edit_text(
        f"Рассылка завершена.\n\nСтатус: {status}\nВсего: {total}\nОтправлено: {success}\nОшибок: {failed}"
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
    raw_code = update.callback_query.data if update.callback_query else ""
    legacy_code_map = {
        "report:details": "moon",
        "v2:moon_detail": "moon",
        "v2:couple_moon": "bridge",
        "v2:venus": "venus",
        "v2:mercury": "mercury",
        "v2:mars": "mars",
        "v2:full_report": "full",
    }
    code = legacy_code_map.get(raw_code, raw_code.replace("p:", ""))
    await _track_event(update, "product_block_opened", block=code, source=raw_code)
    await _delete_callback_menu_message(update, context)
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
        await _tracked_reply_text(
            update, context, premium_paywall_text("details"), reply_markup=premium_keyboard("details")
        )
        return
    if code == "full":
        await _tracked_reply_text(
            update,
            context,
            "📖 Расширенная карта гармонии пары готова. Откройте её в отдельном окне: внутри будет полный разбор и блок применения в жизни — для понимания партнёра, мягких разговоров и гармонизации отношений.",
            reply_markup=detail_card_keyboard("full"),
        )
        return
    if code == "portrait":
        await _tracked_reply_text(
            update,
            context,
            format_couple_portraits_short_card(man_report, woman_report),
            reply_markup=detail_card_keyboard("portrait"),
        )
        return
    if code == "bridge":
        await _send_bridge_teaser_with_menu(
            update,
            context,
            format_couple_moon_bridge_short_card(man_report, woman_report),
        )
        return
    if code not in {"moon", "venus", "mercury", "mars", "jupiter"}:
        await _tracked_reply_text(
            update,
            context,
            "Этот блок пока не найден.",
            reply_markup=after_bridge_keyboard(),
        )
        return
    product_key = PAID_PLANET_PRODUCTS.get(code)
    locked = bool(product_key) and not await _has_premium_access(update, context, product_key, report_id)
    await _tracked_reply_text(
        update,
        context,
        format_planet_short_card(man_report, code),
        reply_markup=detail_card_keyboard(code, locked=locked),
    )


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
        if update.callback_query and update.callback_query.message:
            try:
                await update.callback_query.message.delete()
                _forget_bot_message(context, update.callback_query.message)
            except Exception:
                pass
        await _tracked_reply_text(update, context, "📖 Меню разбора", reply_markup=read_menu_keyboard())
        return
    if product_key.startswith("planet:"):
        planet_code = product_key.replace("planet:", "", 1)
        product_key = PAID_PLANET_PRODUCTS.get(planet_code, "details")
    if product_key not in {"details", "message", *PAID_PLANET_PRODUCTS.values()}:
        product_key = "details"
    await _track_event(update, "premium_paywall_viewed", product_key=product_key)
    await _tracked_reply_text(
        update, context, premium_paywall_text(product_key), reply_markup=premium_keyboard(product_key)
    )


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
    message = update.effective_message
    user_id = _user_id(update)
    if not message or user_id is None:
        return
    if settings.yookassa_enabled:
        await _track_event(update, "premium_yookassa_payment_started", product_key=product_key, report_id=report_id)
        try:
            payment = await asyncio.to_thread(
                create_yookassa_payment,
                shop_id=settings.yookassa_shop_id or "",
                secret_key=settings.yookassa_secret_key or "",
                product=product,
                product_key=product_key,
                report_id=report_id,
                user_id=user_id,
                return_url=settings.webapp_url,
            )
        except RuntimeError:
            logger.exception("YOOKASSA_CREATE_FAILED")
            await _track_event(update, "premium_yookassa_create_failed", product_key=product_key, report_id=report_id)
            await _tracked_reply_text(
                update,
                context,
                "Не получилось создать платёж ЮKassa. Попробуйте ещё раз чуть позже.",
                reply_markup=premium_keyboard(product_key),
            )
            return
        if not payment.confirmation_url or not payment.payment_id:
            await _tracked_reply_text(
                update,
                context,
                "ЮKassa не вернула ссылку на оплату. Попробуйте ещё раз чуть позже.",
                reply_markup=premium_keyboard(product_key),
            )
            return
        context.user_data[PENDING_YOOKASSA_PAYMENT] = {
            "payment_id": payment.payment_id,
            "product_key": product_key,
            "report_id": report_id,
        }
        await _tracked_reply_text(
            update,
            context,
            f"Оплата {product.title}: {product.rubles} ₽. После оплаты вернитесь сюда и нажмите проверку.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("Оплатить в ЮKassa", url=payment.confirmation_url)],
                    [InlineKeyboardButton("✅ Проверить оплату", callback_data=f"premium:check:{payment.payment_id}")],
                    [InlineKeyboardButton("📖 Меню", callback_data="premium:back")],
                ]
            ),
        )
        return
    await _track_event(update, "premium_invoice_opened", product_key=product_key, report_id=report_id)
    await context.bot.send_invoice(
        chat_id=message.chat_id,
        title=product.title,
        description=product.description,
        payload=make_payload(product_key, report_id),
        provider_token=PROVIDER_TOKEN_STARS,
        currency=CURRENCY_STARS,
        prices=[product.price],
    )


async def yookassa_payment_check(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
    await _remember_user(update)
    callback_payment_id = ""
    if query and query.data:
        callback_payment_id = (
            query.data.replace("premium:check:", "", 1) if query.data.startswith("premium:check:") else ""
        )
    pending = context.user_data.get(PENDING_YOOKASSA_PAYMENT)
    if not settings.yookassa_enabled:
        await _tracked_reply_text(
            update,
            context,
            "Оплата ЮKassa сейчас не настроена. Откройте оплату ещё раз.",
            reply_markup=after_bridge_keyboard(),
        )
        return
    payment_id = callback_payment_id
    product_key = ""
    report_id = 0
    if isinstance(pending, dict) and (not payment_id or payment_id == str(pending.get("payment_id", ""))):
        payment_id = str(pending.get("payment_id", ""))
        product_key = str(pending.get("product_key", ""))
        try:
            report_id = int(pending.get("report_id", 0))
        except (TypeError, ValueError):
            report_id = 0
    if not payment_id:
        await _tracked_reply_text(
            update, context, "Активный платёж не найден. Откройте оплату ещё раз.", reply_markup=after_bridge_keyboard()
        )
        return
    try:
        payment = await asyncio.to_thread(
            get_yookassa_payment,
            shop_id=settings.yookassa_shop_id or "",
            secret_key=settings.yookassa_secret_key or "",
            payment_id=payment_id,
        )
    except RuntimeError:
        logger.exception("YOOKASSA_CHECK_FAILED")
        await _tracked_reply_text(update, context, "Не получилось проверить оплату. Попробуйте ещё раз через минуту.")
        return
    product_key = product_key or payment.product_key
    report_id = report_id or payment.report_id
    user_id = _user_id(update)
    if product_key not in {"details", "message"} or report_id <= 0:
        await _tracked_reply_text(
            update, context, "Не получилось связать платёж с Premium-разбором. Откройте оплату ещё раз."
        )
        return
    if payment.telegram_user_id and user_id is not None and payment.telegram_user_id != user_id:
        await _tracked_reply_text(update, context, "Этот платёж создан для другого Telegram-пользователя.")
        return
    await _track_event(
        update, "premium_yookassa_payment_checked", product_key=product_key, report_id=report_id, status=payment.status
    )
    if not payment.paid or payment.status != "succeeded":
        await _tracked_reply_text(
            update,
            context,
            "Пока не вижу успешную оплату. Если вы только что оплатили, подождите несколько секунд и нажмите проверку ещё раз.",
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("✅ Проверить оплату", callback_data=f"premium:check:{payment_id}")]]
            ),
        )
        return
    if user_id is not None:
        await asyncio.to_thread(get_store().grant_entitlement, user_id, product_key, report_id, payment.payment_id)
    context.user_data.pop(PENDING_YOOKASSA_PAYMENT, None)
    await _track_event(
        update, "premium_payment_succeeded", product_key=product_key, report_id=report_id, provider="yookassa"
    )
    await _tracked_reply_text(
        update,
        context,
        "Готово — Premium открыт для этой карты пары. Выберите, что посмотреть первым.",
        reply_markup=after_bridge_keyboard(),
    )


async def precheckout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.pre_checkout_query
    if query is None:
        return
    parsed = parse_payload(query.invoice_payload)
    if parsed is None:
        await query.answer(
            ok=False, error_message="Не получилось распознать продукт. Попробуйте открыть оплату заново."
        )
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
        await _tracked_reply_text(
            update, context, premium_paywall_text("message"), reply_markup=premium_keyboard("message")
        )
        return
    wait = await _tracked_reply_text(update, context, "Собираю общий ориентир для сообщения…")
    text = format_message_guidance(report)
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
    app = ApplicationBuilder().token(settings.telegram_bot_token).post_init(_post_init).build()
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
            CallbackQueryHandler(start_man, pattern=r"^(start_man|partner:start|v2:man:start)$"),
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
            CallbackQueryHandler(cancel, pattern=r"^(cancel|flow:cancel)$"),
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
            CallbackQueryHandler(cancel, pattern=r"^(cancel|flow:cancel)$"),
            CommandHandler("cancel", cancel),
        ],
        allow_reentry=True,
    )
    app.add_handler(man_flow)
    app.add_handler(self_flow)
    app.add_handler(CommandHandler("profile", profile))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("about", about))
    app.add_handler(CommandHandler("daily", daily_key))
    app.add_handler(CommandHandler("today_key", today_key))
    app.add_handler(CommandHandler("stars", star_goal))
    app.add_handler(CommandHandler("broadcast_daily_key", broadcast_daily_key))
    app.add_handler(CommandHandler("broadcast_mercury", broadcast_mercury))
    app.add_handler(CallbackQueryHandler(history, pattern=r"^(history|history:show)$"))
    app.add_handler(CallbackQueryHandler(daily_key, pattern=r"^daily_key$"))
    app.add_handler(CallbackQueryHandler(about, pattern=r"^help:about$"))
    app.add_handler(CallbackQueryHandler(star_goal, pattern=r"^star_goal$"))
    app.add_handler(
        CallbackQueryHandler(
            premium_offer, pattern=r"^premium:(details|message|back|planet:(venus|mercury|mars|jupiter))$"
        )
    )
    app.add_handler(
        CallbackQueryHandler(
            premium_buy,
            pattern=r"^premium:buy:(details|message|planet_venus|planet_mercury|planet_mars|planet_jupiter)$",
        )
    )
    app.add_handler(CallbackQueryHandler(yookassa_payment_check, pattern=r"^premium:check(?::.+)?$"))
    app.add_handler(
        CallbackQueryHandler(
            product_detail,
            pattern=r"^(p:(moon|venus|mercury|mars|jupiter|portrait|full|bridge)|report:details|v2:(moon_detail|couple_moon|venus|mercury|mars|full_report))$",
        )
    )
    app.add_handler(CallbackQueryHandler(message_hint, pattern=r"^(message|report:message)$"))
    app.add_handler(PreCheckoutQueryHandler(precheckout_callback))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_text))
    return app


def main() -> None:
    logger.info("BOT_BOOT: Python %s on %s", platform.python_version(), platform.platform())
    logger.info("BOT_BOOT: %s", settings.diagnostic_summary())
    logger.info("BOT_BOOT: starting couple harmony flow")
    start_webapp_server()
    build_application().run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
