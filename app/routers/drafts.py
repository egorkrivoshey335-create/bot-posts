"""Drafts management handlers."""

import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

logger = logging.getLogger(__name__)

router = Router(name="drafts")


@router.message(Command("drafts"))
async def cmd_list_drafts(message: Message) -> None:
    """Show list of drafts."""
    logger.info(f"User {message.from_user.id} requested drafts list")
    
    # TODO: Implement drafts list with pagination
    await message.answer(
        "📋 <b>Ваши черновики</b>\n\n"
        "<i>Черновиков пока нет.</i>\n\n"
        "Создайте новый пост командой /new"
    )


# TODO: Implement handlers:
# - View draft details
# - Edit draft text
# - Edit draft media
# - Edit draft buttons
# - Delete draft
# - Schedule draft
# - Publish draft immediately
