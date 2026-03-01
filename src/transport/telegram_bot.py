"""Telegram transport for the Resource Librarian agent."""

from __future__ import annotations

import asyncio
import logging
from typing import List, Optional

from aiogram import Bot, Dispatcher, Router
from aiogram.enums import ChatAction, ChatType
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import Message
from langchain_core.messages import HumanMessage

from src.agent.graph import graph
from src.core.config import settings
from src.pairing.store import (
    PairingCodeNotFound,
    PairingLimitReached,
    PairingStore,
)


logger = logging.getLogger(__name__)


def _format_human_name(message: Message) -> str:
    parts: List[str] = []
    if message.from_user:
        if message.from_user.first_name:
            parts.append(message.from_user.first_name)
        if message.from_user.last_name:
            parts.append(message.from_user.last_name)
    return " ".join(parts) if parts else "Unknown"


async def _notify_admin(bot: Bot, text: str, admin_id: int) -> None:
    try:
        await bot.send_message(admin_id, text)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Failed to notify admin %s: %s", admin_id, exc)


async def _notify_user(bot: Bot, user_id: int, text: str) -> None:
    try:
        await bot.send_message(user_id, text)
    except Exception as exc:  # pragma: no cover - best effort
        logger.warning("Failed to send Telegram DM to %s: %s", user_id, exc)


class TelegramAgentBot:
    def __init__(self) -> None:
        if not settings.telegram_bot_token:
            raise RuntimeError(
                "TELEGRAM_BOT_TOKEN is not configured; unable to start Telegram bot"
            )

        self._bot = Bot(token=settings.telegram_bot_token.get_secret_value())
        self._dispatcher = Dispatcher()
        self._router = Router()
        self._store = PairingStore()
        admin_id = settings.telegram_admin_id
        if admin_id is None:
            raise RuntimeError(
                "TELEGRAM_ADMIN_ID is not configured; unable to enforce pairing approvals"
            )
        self._admin_id: int = admin_id

        self._register_handlers()

    def _register_handlers(self) -> None:
        self._router.message.register(self._handle_start, CommandStart())
        self._router.message.register(self._handle_help, Command("help"))
        self._router.message.register(self._handle_status, Command("status"))
        self._router.message.register(self._pairing_command, Command("pairing"))
        self._router.message.register(self._handle_message)
        self._dispatcher.include_router(self._router)

    async def run(self) -> None:
        poll_interval = settings.telegram_poll_interval
        await self._dispatcher.start_polling(
            self._bot,
            polling_timeout=max(int(poll_interval), 1),
        )

    # ----- Command handlers -----------------------------------------
    async def _handle_start(self, message: Message) -> None:
        await message.answer(
            "Hi! I'm your Resource Librarian bot. Send me a resource to save or ask for saved items."
        )
        await self._handle_status(message)

    async def _handle_help(self, message: Message) -> None:
        help_text = (
            "Use this bot to interact with your Supabase-backed resource library.\n"
            "• Send 'save <url> under <tag>' to store items.\n"
            "• Ask 'find resources about X' to retrieve items.\n"
            "If you're new here, your access request will be sent to the admin for approval."
        )
        await message.answer(help_text)

    async def _handle_status(self, message: Message) -> None:
        user_id = message.from_user.id if message.from_user else None
        if user_id is None:
            await message.answer("Unable to read your Telegram ID.")
            return

        if self._store.is_allowed(user_id):
            await message.answer("You're approved to chat with the agent. Send a prompt anytime.")
            return

        pending = next((req for req in self._store.list_pending() if req.user_id == user_id), None)
        if pending:
            await message.answer(
                f"Your pairing request is pending approval. Share code {pending.code} with the admin."
            )
        else:
            await message.answer(
                "You're not paired yet. Send a message and I'll create a pairing code for the admin."
            )

    async def _pairing_command(self, message: Message, command: CommandObject) -> None:
        user_id = message.from_user.id if message.from_user else None
        if user_id != self._admin_id:
            await message.answer("Only admins can manage pairing requests.")
            return

        args = (command.args or "").strip().split()
        if not args:
            await message.answer(
                "Usage: /pairing list | approve <CODE> | reject <CODE> | revoke <USER_ID>"
            )
            return

        action = args[0].lower()
        if action == "list":
            pending = self._store.list_pending()
            if not pending:
                await message.answer("No pending pairing requests.")
                return
            lines = [
                "Pending requests:" + "\n" + "\n".join(
                    f"• {req.code} — {req.username or req.user_id} "
                    f"({req.user_id}), requested {req.requested_at.isoformat()}"
                    for req in pending
                )
            ]
            await message.answer("\n".join(lines))
            return

        if action in {"approve", "reject"}:
            if len(args) < 2:
                await message.answer(f"Usage: /pairing {action} <CODE>")
                return
            code = args[1]
            try:
                if action == "approve":
                    req = self._store.approve(code)
                    await message.answer(f"Approved {req.user_id} with code {req.code}.")
                    await _notify_user(
                        self._bot,
                        req.user_id,
                        "You're approved to chat with the Resource Librarian bot. Send a message anytime!",
                    )
                else:
                    req = self._store.reject(code)
                    await message.answer(f"Rejected pairing request {req.code} ({req.user_id}).")
                    await _notify_user(
                        self._bot,
                        req.user_id,
                        "Your pairing request was rejected. Reply to request a new code if needed.",
                    )
            except PairingCodeNotFound as exc:
                await message.answer(str(exc))
            return

        if action == "revoke":
            if len(args) < 2:
                await message.answer("Usage: /pairing revoke <USER_ID>")
                return
            target_id = int(args[1])
            self._store.revoke(target_id)
            await message.answer(f"Revoked access for user {target_id} (if previously approved).")
            await _notify_user(
                self._bot,
                target_id,
                "Your Telegram access to the Resource Librarian bot was revoked by an admin.",
            )
            return

        await message.answer(
            "Unknown pairing action. Use list, approve <CODE>, reject <CODE>, or revoke <USER_ID>."
        )

    # ----- Message handler ------------------------------------------
    async def _handle_message(self, message: Message) -> None:
        if message.chat.type not in {ChatType.PRIVATE, ChatType.SUPERGROUP}:
            await message.answer("Please DM me directly for now.")
            return

        if not message.text:
            await message.answer("Please send plain text messages.")
            return

        if not message.from_user:
            await message.answer("Unable to read your Telegram profile. Try again later.")
            return

        user_id = message.from_user.id

        if not self._store.is_allowed(user_id):
            await self._handle_unpaired_user(message)
            return

        await self._respond_with_agent(message)

    async def _handle_unpaired_user(self, message: Message) -> None:
        user = message.from_user
        if not user:
            await message.answer("Unable to read your Telegram profile. Try again later.")
            return
        try:
            req, is_new = self._store.register_request(
                user_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                message_preview=message.text,
            )
        except PairingLimitReached as exc:
            await message.answer(
                "The pairing queue is full right now. Please wait for an approval and try again."
            )
            logger.info("Pairing queue full when %s messaged: %s", user.id, exc)
            return

        if is_new:
            await message.answer(
                "Thanks! A pairing code was sent to the admin. Share this code with them: "
                f"{req.code}."
            )
            admin_text = (
                "New Telegram pairing request\n"
                f"• Code: {req.code}\n"
                f"• User: @{user.username or user.id}\n"
                f"• Name: {_format_human_name(message)}\n"
                f"• Preview: {req.message_preview or 'N/A'}"
            )
            await _notify_admin(self._bot, admin_text, self._admin_id)
        else:
            await message.answer(
                "Your pairing request is still pending approval. Share code "
                f"{req.code} with the admin."
            )

    async def _respond_with_agent(self, message: Message) -> None:
        await self._bot.send_chat_action(message.chat.id, ChatAction.TYPING)
        prompt = (message.text or "").strip()
        if not prompt:
            await message.answer("Please send some text so I can help.")
            return
        try:
            result = await graph.ainvoke({"messages": [HumanMessage(content=prompt)]})
            response_message = str(result["messages"][-1].content)
        except Exception as exc:  # pragma: no cover - relies on runtime graph behaviour
            logger.exception("Telegram agent execution failed: %s", exc)
            response_message = (
                "The agent hit an unexpected error while processing your request."
                " Please try again in a minute."
            )
        await message.answer(response_message)


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = TelegramAgentBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
