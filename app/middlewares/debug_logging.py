"""Debug logging middleware for all incoming messages."""

import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)


class DebugLoggingMiddleware(BaseMiddleware):
    """Middleware that logs all incoming messages for debugging."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Log message details and pass to next handler."""
        if isinstance(event, Message):
            # Get FSM state if available
            state: FSMContext = data.get("state")
            current_state = None
            if state:
                current_state = await state.get_state()

            # Get user info
            user_id = event.from_user.id if event.from_user else "NO_USER"
            username = event.from_user.username if event.from_user else None

            # Log message details
            logger.info(
                f"📨 INCOMING MESSAGE | "
                f"user_id={user_id} (@{username}) | "
                f"chat_id={event.chat.id} | "
                f"content_type={event.content_type} | "
                f"text={repr(event.text)[:50] if event.text else None} | "
                f"caption={repr(event.caption)[:50] if event.caption else None} | "
                f"has_photo={bool(event.photo)} | "
                f"has_video={bool(event.video)} | "
                f"has_document={bool(event.document)} | "
                f"state={current_state}"
            )

            if event.from_user is None:
                logger.warning("⚠️ Message received with from_user=None!")

        # Always pass to the next handler
        return await handler(event, data)
