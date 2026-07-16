from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app import ad_attribution

_INSTALLED = False


def upload_conversion(row: dict[str, Any]) -> str:
    counter_id = ad_attribution._counter_id()
    oauth_token = ad_attribution._oauth_token()
    if not counter_id or not oauth_token:
        raise RuntimeError("YANDEX_METRICA_ID or YANDEX_METRICA_OAUTH_TOKEN is not configured")

    body, boundary = ad_attribution._multipart(ad_attribution.conversion_csv(row))
    request = Request(
        ad_attribution.UPLOAD_URL.format(counter_id=counter_id),
        data=body,
        method="POST",
        headers={
            "Authorization": f"OAuth {oauth_token}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
            "Accept": "application/json",
            "User-Agent": "partner-key-bot/1.1",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except HTTPError as exc:
        details = exc.read().decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"Metrica HTTP {exc.code}: {details}") from exc
    except URLError as exc:
        raise RuntimeError(f"Metrica network error: {exc.reason}") from exc

    uploading = payload.get("uploading") if isinstance(payload, dict) else None
    if not isinstance(uploading, dict):
        raise RuntimeError("Metrica returned no uploading object")
    upload_id = str(uploading.get("id") or "").strip()
    if not upload_id.isdigit():
        raise RuntimeError("Metrica accepted the file but returned no upload id")
    return upload_id


def install() -> None:
    global _INSTALLED
    if _INSTALLED:
        return
    ad_attribution.upload_conversion = upload_conversion
    _INSTALLED = True
