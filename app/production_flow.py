from __future__ import annotations

import app.woman_flow as base
from app import (
    ad_attribution,
    ad_landing,
    analytics_diagnostics,
    bridge_navigation,
    button_contracts,
    content_admin_access,
    entertaining_flow,
    full_map_contract,
    message_retirement,
    metrica_layer,
    metrica_legacy_queue,
    metrica_reliability,
    metrica_revenue_guard,
    metrica_upload_api,
    payment_reconciliation,
    topic_labels,
)


WELCOME_TEXT = """
💞 Астро Партнёр
Инструкция к вашему мужчине

Он может любить — и показывать это совсем не так, как вы ожидаете.

По дате рождения вы получите первый персональный ключ:

• что может помогать ему расслабляться и идти навстречу;
• какие проявления любви и заботы он особенно замечает;
• что может создавать напряжение и закрывать контакт;
• какую фразу или действие попробовать сегодня.

🗓 Для первого разбора достаточно даты рождения мужчины. Точное время необязательно.

🤍 Это не оценка совместимости и не готовый вывод о человеке, а подсказка, которую можно проверить в живом общении.

👇 Получить первый ключ бесплатно
""".strip()


# Финальный production-слой: сохраняем новую механику продукта,
# возвращаем одобренное первое сообщение и подключаем аналитику.
base.WELCOME_TEXT = WELCOME_TEXT
entertaining_flow.current.WELCOME_TEXT = WELCOME_TEXT
metrica_layer.install()
ad_attribution.install(base)
ad_landing.install()
metrica_upload_api.install()
metrica_reliability.install()
metrica_legacy_queue.install()
metrica_revenue_guard.install()
analytics_diagnostics.install()
button_contracts.install()
full_map_contract.install()
payment_reconciliation.install()
bridge_navigation.install()
topic_labels.install()
message_retirement.install()
content_admin_access.install()


def main() -> None:
    entertaining_flow.main()


if __name__ == "__main__":
    main()
