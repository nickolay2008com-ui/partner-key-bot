from __future__ import annotations

import logging

from openai import OpenAI

from app.astro.report import PartnerReport, format_message_templates
from app.config import settings

logger = logging.getLogger(__name__)


def openai_available() -> bool:
    return bool(settings.openai_api_key)


def build_partner_message_with_ai(report: PartnerReport) -> str:
    """Generate a softer message pack through OpenAI, with a deterministic fallback.

    The MVP must not depend on OpenAI being healthy. If API key is absent,
    quota is exhausted, or the network fails, we return local templates.
    """
    fallback = format_message_templates(report)
    if not settings.openai_api_key:
        return fallback

    client = OpenAI(api_key=settings.openai_api_key)
    system_prompt = """
Ты пишешь короткие, бережные сообщения для общения с партнёром.
Нельзя манипулировать, давить, обвинять, ставить диагнозы или обещать исход.
Тон: взрослый, спокойный, мягкий, ясный.
Пиши на русском языке.
Верни 3 готовых варианта сообщения:
1) очень короткий;
2) тёплый;
3) честный разговор без давления.
После вариантов добавь одну строку: «Как использовать: ...».
""".strip()
    user_prompt = f"""
Партнёр: {report.partner_name}
Дата рождения: {report.birth_date}
Эмоциональный язык: {report.emotional_language_title}
Краткий смысл: {report.summary}
Базовые варианты:
{format_message_templates(report)}
""".strip()

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
        )
        text = (response.output_text or "").strip()
        if not text:
            return fallback
        return f"✍️ Что можно написать: {report.partner_name}\n\n{text}"
    except Exception as exc:
        logger.exception("OpenAI message generation failed: %s", exc)
        return (
            fallback
            + "\n\nGPT-вариант временно не собрался, поэтому показываю базовые тексты. Внешние API иногда тоже изображают загадочную Луну."
        )
