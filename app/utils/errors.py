"""Error handling utilities."""

import logging
from functools import wraps
from typing import Callable, TypeVar

from aiogram.types import Message, CallbackQuery

logger = logging.getLogger(__name__)

T = TypeVar("T")


class BotError(Exception):
    """Base exception for bot errors."""
    
    def __init__(self, message: str, user_message: str = "Произошла ошибка"):
        self.message = message
        self.user_message = user_message
        super().__init__(message)


class PermissionError(BotError):
    """User doesn't have required permissions."""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, "⛔ У вас нет доступа к этой функции")


class NotFoundError(BotError):
    """Requested resource not found."""
    
    def __init__(self, resource: str = "Resource"):
        super().__init__(
            f"{resource} not found",
            f"❌ {resource} не найден"
        )


class ValidationError(BotError):
    """Input validation failed."""
    
    def __init__(self, message: str, user_message: str):
        super().__init__(message, user_message)


class PublishingError(BotError):
    """Error during post publishing."""
    
    def __init__(self, message: str):
        super().__init__(
            message,
            "❌ Ошибка при публикации. Попробуйте позже."
        )


def handle_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator to handle common bot errors."""
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except BotError as e:
            logger.error(f"BotError in {func.__name__}: {e.message}")
            
            # Try to send error message to user
            for arg in args:
                if isinstance(arg, Message):
                    await arg.answer(e.user_message)
                    break
                elif isinstance(arg, CallbackQuery):
                    await arg.answer(e.user_message, show_alert=True)
                    break
        except Exception as e:
            logger.exception(f"Unexpected error in {func.__name__}: {e}")
            
            # Try to send generic error message
            for arg in args:
                if isinstance(arg, Message):
                    await arg.answer("❌ Произошла непредвиденная ошибка")
                    break
                elif isinstance(arg, CallbackQuery):
                    await arg.answer("❌ Ошибка", show_alert=True)
                    break
    
    return wrapper
