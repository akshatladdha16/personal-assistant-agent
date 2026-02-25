from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from langchain_core.messages import HumanMessage

from src.agent.graph import graph
from src.core.config import settings

from .client import WPPConnectClient

logger = logging.getLogger(__name__)


class WebhookPayload(BaseModel):
    event: str
    session: Optional[str] = None
    data: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


def create_app() -> FastAPI:
    app = FastAPI(title="Resource Librarian WhatsApp Bridge", version="0.1.0")

    @app.on_event("startup")
    async def startup_event() -> None:
        token = (
            settings.wppconnect_token.get_secret_value()
            if settings.wppconnect_token
            else None
        )
        session = settings.wppconnect_session

        if not session or not token:
            raise RuntimeError(
                "WPPConnect session name and token must be configured before starting the bridge"
            )

        app.state.whatsapp_client = WPPConnectClient(
            base_url=settings.wppconnect_base_url,
            session=session,
            token=token,
        )
        logger.info(
            "WhatsApp bridge started for session '%s' using WPPConnect at %s",
            session,
            settings.wppconnect_base_url,
        )

    @app.on_event("shutdown")
    async def shutdown_event() -> None:
        client: Optional[WPPConnectClient] = getattr(app.state, "whatsapp_client", None)
        if client:
            await client.close()

    def verify_secret(
        x_wppconnect_secret: Optional[str] = Header(default=None),
    ) -> None:
        secret = (
            settings.wppconnect_webhook_secret.get_secret_value()
            if settings.wppconnect_webhook_secret
            else None
        )
        if secret and x_wppconnect_secret != secret:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid webhook secret")

    @app.post("/webhooks/wppconnect")
    async def handle_webhook(
        payload: WebhookPayload,
        request: Request,
        _=Depends(verify_secret),
    ) -> JSONResponse:
        if payload.session and settings.wppconnect_session:
            if payload.session != settings.wppconnect_session:
                return JSONResponse(
                    {"status": "ignored", "reason": "session_mismatch"},
                    status_code=status.HTTP_202_ACCEPTED,
                )

        if payload.event not in {"onMessage", "onAnyMessage"}:
            return JSONResponse(
                {"status": "ignored", "reason": "unsupported_event"},
                status_code=status.HTTP_202_ACCEPTED,
            )

        message = payload.data or {}
        if message.get("fromMe"):
            return JSONResponse({"status": "skipped", "reason": "self_message"})

        if message.get("isGroupMsg"):
            return JSONResponse({"status": "skipped", "reason": "group_message"})

        text_content = (message.get("body") or message.get("text") or "").strip()
        if not text_content:
            return JSONResponse({"status": "skipped", "reason": "empty_content"})

        sender = message.get("from") or ""
        chat_id = message.get("chatId")

        human_message = HumanMessage(
            content=text_content,
            metadata={
                "transport": "whatsapp",
                "sender": sender,
                "chat_id": chat_id,
                "payload": message,
            },
        )

        try:
            result = await graph.ainvoke({"messages": [human_message]})
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Agent execution failed: %s", exc)
            return JSONResponse(
                {
                    "status": "error",
                    "reason": "agent_failure",
                    "detail": str(exc),
                },
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        messages = result.get("messages", [])
        if messages:
            final_message = messages[-1]
            response_text = getattr(final_message, "content", "").strip()
        else:
            logger.warning("Agent returned no messages for WhatsApp input")
            response_text = ""
        if not response_text:
            response_text = "I wasn't able to generate a response just now."

        client: WPPConnectClient = request.app.state.whatsapp_client

        try:
            await client.send_text(
                recipient=sender,
                chat_id=chat_id,
                message=response_text,
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("Failed to send WhatsApp message: %s", exc)
            return JSONResponse(
                {
                    "status": "error",
                    "reason": "delivery_failed",
                    "detail": str(exc),
                },
                status_code=status.HTTP_502_BAD_GATEWAY,
            )

        return JSONResponse({"status": "ok"})

    @app.get("/healthz")
    async def healthz() -> Dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
