from __future__ import annotations

import app.woman_flow as base
from app import (
    ad_attribution,
    entertaining_flow,
    metrica_layer,
    metrica_reliability,
    metrica_upload_api,
)


WELCOME_TEXT = """
💞 Астро Партнёр
Инструкция к вашему мужчине

📦 К каждому устройству прилагается инструкция.
💌 К мужчине, которого вы любите, почему-то нет.

✨ Мы решили это исправить.

За 2 минуты получите первый ключ к нему бесплатно:

• что помогает ему расслабиться и идти навстречу;
• что он воспринимает как любовь и заботу;
• что может незаметно закрывать контакт;
• какую фразу или действие попробовать сегодня.

🗓 Нужна только дата рождения мужчины. Точное время необязательно.

🤍 Это не проверка совместимости и не приговор отношениям.
🧭 Это карта понимания: меньше догадок, больше тепла, ясности и действий, которые можно проверить по его живой реакции.

👇 Нажмите кнопку и получите первый ключ к нему бесплатно.
""".strip()


# Финальный production-слой: сохраняем новую механику продукта,
# возвращаем одобренное первое сообщение и подключаем аналитику.
base.WELCOME_TEXT = WELCOME_TEXT
entertaining_flow.current.WELCOME_TEXT = WELCOME_TEXT
metrica_layer.install()
ad_attribution.install(base)
metrica_upload_api.install()
metrica_reliability.install()


def main() -> None:
    entertaining_flow.main()


if __name__ == "__main__":
    main()
