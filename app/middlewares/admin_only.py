"""Admin-only access middleware."""

import logging
from typing import Any, Awaitable, Callable, Dict, List

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class AdminOnlyMiddleware(BaseMiddleware):
    """Middleware that allows only admins to use the bot."""

    def __init__(self, admin_ids: List[int]):
        """Initialize middleware with list of admin user IDs."""
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        """Process incoming event and check if user is admin."""
        user = None
        
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user
        
        if user is None:
            return await handler(event, data)
        
        if user.id not in self.admin_ids:
            logger.warning(
                f"Unauthorized access attempt by user {user.id} ({user.username})"
            )
            
            if isinstance(event, Message):
                await event.answer(
                    "⛔ У вас нет доступа к этому боту.\n"
                    "Обратитесь к администратору."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⛔ У вас нет доступа",
                    show_alert=True,
                )
            return None
        
        return await handler(event, data)
