from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()


def _parse_ids(value: str | None) -> set[int]:
    if not value:
        return set()
    result: set[int] = set()
    for raw in value.split(","):
        item = raw.strip()
        if not item:
            continue
        try:
            result.add(int(item))
        except ValueError:
            raise ValueError(f"Список Telegram ID содержит не число: {item}") from None
    return result


def _normalize_webapp_url(value: str | None) -> str:
    url = (value or "https://partner-key.up.railway.app/webapp").strip()
    if not url:
        url = "https://partner-key.up.railway.app/webapp"
    if not url.startswith(("https://", "http://")):
        url = f"https://{url}"
    parsed = urlparse(url)
    if not parsed.path or parsed.path == "/":
        url = url.rstrip("/") + "/webapp"
    return url


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    app_timezone: str
    authorized_telegram_ids: set[int]
    broadcast_admin_ids: set[int]
    webapp_url: str
    data_dir: Path
    openai_api_key: str | None
    openai_model: str

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        data_dir_value = os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH") or "data"
        data_dir = Path(data_dir_value).expanduser()
        return cls(
            telegram_bot_token=token,
            app_timezone=os.getenv("APP_TIMEZONE", "Europe/Moscow").strip() or "Europe/Moscow",
            authorized_telegram_ids=_parse_ids(os.getenv("AUTHORIZED_TELEGRAM_IDS")),
            broadcast_admin_ids=_parse_ids(os.getenv("BROADCAST_ADMIN_IDS")),
            webapp_url=_normalize_webapp_url(os.getenv("WEBAPP_URL")),
            data_dir=data_dir,
            openai_api_key=os.getenv("OPENAI_API_KEY", "").strip() or None,
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        )

    def validate_runtime(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Добавь токен бота в Railway Variables или .env")
        self.data_dir.mkdir(parents=True, exist_ok=True)

    @property
    def reports_db_path(self) -> Path:
        return self.data_dir / "partner_reports.sqlite3"

    def diagnostic_summary(self) -> str:
        access = "restricted" if self.authorized_telegram_ids else "public"
        openai = "enabled" if self.openai_api_key else "disabled"
        broadcast_admins = len(self.broadcast_admin_ids | self.authorized_telegram_ids)
        return f"timezone={self.app_timezone}; access={access}; openai={openai}; data_dir={self.data_dir}; broadcast_admins={broadcast_admins}; webapp_url={self.webapp_url}"


settings = Settings.from_env()
