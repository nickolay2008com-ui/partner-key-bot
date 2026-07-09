from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


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


def _default_data_dir() -> str:
    explicit = os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
    if explicit:
        return explicit
    if os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID"):
        return "/data"
    return "data"


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
    database_url: str | None
    yookassa_shop_id: str | None
    yookassa_secret_key: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
        data_dir_value = _default_data_dir()
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
            database_url=os.getenv("DATABASE_URL", "").strip() or None,
            yookassa_shop_id=(os.getenv("YOOKASSA_SHOP_ID") or os.getenv("YUKASSA_SHOP_ID") or "").strip() or None,
            yookassa_secret_key=(os.getenv("YOOKASSA_SECRET_KEY") or os.getenv("YUKASSA_SECRET") or "").strip() or None,
        )

    def validate_runtime(self) -> None:
        if not self.telegram_bot_token:
            raise RuntimeError("TELEGRAM_BOT_TOKEN не задан. Добавь токен бота в Railway Variables или .env")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        if self.database_url:
            return
        if (os.getenv("RAILWAY_ENVIRONMENT") or os.getenv("RAILWAY_PROJECT_ID")) and not (
            os.getenv("DATA_DIR") or os.getenv("RAILWAY_VOLUME_MOUNT_PATH")
        ):
            logger.warning(
                "DATA_DIR is not configured on Railway; using %s. "
                "Attach a Railway Volume mounted to this path or profile data will still be lost on redeploy.",
                self.data_dir,
            )

    @property
    def yookassa_enabled(self) -> bool:
        return bool(self.yookassa_shop_id and self.yookassa_secret_key)

    def reports_db_path(self) -> Path:
        return self.data_dir / "partner_reports.sqlite3"

    def diagnostic_summary(self) -> str:
        access = "restricted" if self.authorized_telegram_ids else "public"
        openai = "enabled" if self.openai_api_key else "disabled"
        broadcast_admins = len(self.broadcast_admin_ids | self.authorized_telegram_ids)
        storage = "postgres" if self.database_url else f"sqlite:{self.data_dir}"
        yookassa = "enabled" if self.yookassa_enabled else "disabled"
        return (
            f"timezone={self.app_timezone}; access={access}; openai={openai}; storage={storage}; "
            f"broadcast_admins={broadcast_admins}; webapp_url={self.webapp_url}; yookassa={yookassa}"
        )


settings = Settings.from_env()
