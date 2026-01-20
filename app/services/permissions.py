"""Permissions checking service."""

import logging
from typing import Optional, Tuple

from aiogram.types import ChatMemberAdministrator, ChatMemberOwner

from app.bot import bot
from app.config import get_settings

logger = logging.getLogger(__name__)


async def check_bot_channel_permissions() -> Tuple[bool, Optional[str]]:
    """
    Check if bot has necessary permissions in the target channel.
    
    Returns:
        Tuple of (has_permissions, error_message)
    """
    settings = get_settings()
    channel_id = settings.channel_id
    
    try:
        bot_info = await bot.get_me()
        member = await bot.get_chat_member(channel_id, bot_info.id)
        
        if not isinstance(member, (ChatMemberAdministrator, ChatMemberOwner)):
            return False, "❌ Бот не является администратором канала."
        
        if isinstance(member, ChatMemberAdministrator):
            if not member.can_post_messages:
                return False, "❌ У бота нет права публиковать сообщения."
            if not member.can_edit_messages:
                return False, "⚠️ У бота нет права редактировать сообщения."
        
        return True, None
        
    except Exception as e:
        logger.error(f"Failed to check bot permissions: {e}")
        return False, f"❌ Ошибка проверки прав: {e}"


async def check_user_is_admin(user_id: int) -> bool:
    """Check if user ID is in admin list."""
    settings = get_settings()
    return user_id in settings.admin_ids


async def get_channel_info() -> Optional[dict]:
    """Get channel information."""
    settings = get_settings()
    
    try:
        chat = await bot.get_chat(settings.channel_id)
        return {
            "id": chat.id,
            "title": chat.title,
            "username": chat.username,
            "type": chat.type,
        }
    except Exception as e:
        logger.error(f"Failed to get channel info: {e}")
        return None
