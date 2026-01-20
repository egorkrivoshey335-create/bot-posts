"""Edit published posts handlers."""

import logging

from aiogram import F, Router
from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

router = Router(name="edit_published")


# TODO: Implement handlers for editing published posts:
# - Edit inline buttons of published message
# - Callback handlers for button management
# - Deep link handling for editing specific message
