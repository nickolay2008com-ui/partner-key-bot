from __future__ import annotations

import app.woman_flow as base
from app import (
    ad_attribution,
    ad_landing,
    analytics_diagnostics,
    bridge_navigation,
    button_contracts,
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
Инструкция к эмоциональному ритму вашего мужчины

Иногда забота сближает. А иногда та же забота воспринимается совсем не так, как вы ожидали.

За 2 минуты получите первый ключ к нему бесплатно:

• что может помогать ему расслабляться и идти на контакт;
• какой формат заботы ему может быть понятнее;
• что иногда заставляет его защищаться или отдаляться;
• какую фразу или действие можно проверить сегодня.

🗓 Нужны имя и дата рождения мужчины. Точное время желательно, но необязательно: если в эту дату Луна меняла знак, я покажу два возможных варианта.

🤍 Это не проверка совместимости и не инструкция, как изменить человека. Вы получите гипотезу, которую можно сравнить с его реальными реакциями.

👇 Начните с первого бесплатного ключа.
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


def main() -> None:
    entertaining_flow.main()


if __name__ == "__main__":
    main()
