"""Reply keyboards (if needed)."""

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def remove_keyboard() -> ReplyKeyboardRemove:
    """Remove reply keyboard."""
    return ReplyKeyboardRemove()


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    """Main reply keyboard (optional)."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📝 Новый пост"),
                KeyboardButton(text="📋 Черновики"),
            ],
            [
                KeyboardButton(text="⏰ Запланированные"),
                KeyboardButton(text="❓ Помощь"),
            ],
        ],
        resize_keyboard=True,
    )
