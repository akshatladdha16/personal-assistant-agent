from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


def _normalise_phone(identifier: Optional[str]) -> Optional[str]:
    """Remove WhatsApp suffixes and non-digit characters from an identifier."""

    if not identifier:
        return None

    phone = identifier
    for suffix in ("@c.us", "@s.whatsapp.net", "@g.us", "@broadcast"):
        if phone.endswith(suffix):
            phone = phone[: -len(suffix)]
            break

    # Remove any non-digit characters except leading '+'
    if phone.startswith("+"):
        return "+" + "".join(ch for ch in phone[1:] if ch.isdigit())
    return "".join(ch for ch in phone if ch.isdigit()) or None


class WPPConnectClient:
    """Thin wrapper around the WPPConnect REST API."""

    def __init__(
        self,
        *,
        base_url: str,
        session: str,
        token: str,
        timeout: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def send_text(
        self,
        *,
        recipient: str,
        message: str,
        chat_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Send a plain text message via WPPConnect."""

        phone = _normalise_phone(recipient)
        payload: Dict[str, Any] = {"message": message}
        if phone:
            payload["phone"] = phone
        if chat_id:
            payload["chatId"] = chat_id

        try:
            response = await self._client.post(
                f"/api/{self._session}/send-message", json=payload
            )
        except httpx.HTTPError as exc:
            logger.error("Failed to call WPPConnect send-message: %s", exc)
            raise

        if response.status_code >= 400:
            logger.error(
                "WPPConnect send-message returned %s: %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()

        return response.json()
