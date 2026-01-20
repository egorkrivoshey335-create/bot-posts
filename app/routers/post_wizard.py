"""Post creation wizard with FSM."""

import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

router = Router(name="post_wizard")


class PostWizard(StatesGroup):
    """States for post creation wizard."""

    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_buttons = State()
    waiting_for_schedule = State()
    confirmation = State()


@router.message(Command("new"))
async def cmd_new_post(message: Message, state: FSMContext) -> None:
    """Start new post creation wizard."""
    logger.info(f"User {message.from_user.id} started new post creation")
    
    await state.set_state(PostWizard.waiting_for_text)
    await message.answer(
        "📝 <b>Создание нового поста</b>\n\n"
        "Отправьте текст поста или медиафайл.\n"
        "Для отмены используйте /cancel"
    )


# TODO: Implement FSM handlers for post creation
# - waiting_for_text: receive text
# - waiting_for_media: receive media files, collect album
# - waiting_for_buttons: parse button format "text - url"
# - waiting_for_schedule: parse datetime or "now"
# - confirmation: show preview and confirm
