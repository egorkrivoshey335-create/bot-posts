"""Inline keyboards for the bot."""

from typing import List, Optional

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Новый пост", callback_data="new_post"),
            InlineKeyboardButton(text="📋 Черновики", callback_data="drafts"),
        ],
        [
            InlineKeyboardButton(text="⏰ Запланированные", callback_data="scheduled"),
        ],
    ])


def post_actions_keyboard(post_id: int, status: str = "draft") -> InlineKeyboardMarkup:
    """Actions for a specific post."""
    buttons = [
        [
            InlineKeyboardButton(text="👁 Превью", callback_data=f"preview:{post_id}"),
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit:{post_id}"),
        ],
    ]
    
    if status == "draft":
        buttons.append([
            InlineKeyboardButton(text="📅 Запланировать", callback_data=f"schedule:{post_id}"),
            InlineKeyboardButton(text="📤 Опубликовать", callback_data=f"publish:{post_id}"),
        ])
    elif status == "scheduled":
        buttons.append([
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel:{post_id}"),
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete:{post_id}"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="drafts"),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def confirm_keyboard(action: str, post_id: int) -> InlineKeyboardMarkup:
    """Confirmation keyboard for dangerous actions."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="✅ Да",
                callback_data=f"confirm:{action}:{post_id}"
            ),
            InlineKeyboardButton(
                text="❌ Нет",
                callback_data=f"cancel_action:{post_id}"
            ),
        ],
    ])


def pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str = "page",
) -> List[InlineKeyboardButton]:
    """Pagination buttons."""
    buttons = []
    
    if current_page > 1:
        buttons.append(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"{callback_prefix}:{current_page - 1}"
        ))
    
    buttons.append(InlineKeyboardButton(
        text=f"{current_page}/{total_pages}",
        callback_data="noop"
    ))
    
    if current_page < total_pages:
        buttons.append(InlineKeyboardButton(
            text="Вперёд ▶️",
            callback_data=f"{callback_prefix}:{current_page + 1}"
        ))
    
    return buttons


def edit_post_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Edit options for a post."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Текст", callback_data=f"edit_text:{post_id}"),
            InlineKeyboardButton(text="🖼 Медиа", callback_data=f"edit_media:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="🔘 Кнопки", callback_data=f"edit_buttons:{post_id}"),
            InlineKeyboardButton(text="⚙️ Настройки", callback_data=f"edit_settings:{post_id}"),
        ],
        [
            InlineKeyboardButton(text="◀️ Назад", callback_data=f"post:{post_id}"),
        ],
    ])


def cancel_keyboard() -> InlineKeyboardMarkup:
    """Simple cancel keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="wizard_cancel")],
    ])


def skip_keyboard(callback_data: str = "skip") -> InlineKeyboardMarkup:
    """Skip step keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="⏭ Пропустить", callback_data=callback_data),
            InlineKeyboardButton(text="❌ Отмена", callback_data="wizard_cancel"),
        ],
    ])


def done_keyboard(callback_data: str = "done") -> InlineKeyboardMarkup:
    """Done/finish keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Готово", callback_data=callback_data),
            InlineKeyboardButton(text="❌ Отмена", callback_data="wizard_cancel"),
        ],
    ])
