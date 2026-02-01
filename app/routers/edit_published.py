"""Edit published posts handlers."""

import logging
from typing import Optional, List

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from app.bot import bot
from app.config import get_settings
from app.db.models import PostStatus
from app.db.repo import DraftPostRepository, DraftButtonRepository
from app.db.session import get_session
from app.keyboards.inline import cancel_keyboard

logger = logging.getLogger(__name__)

router = Router(name="edit_published")


class EditPost(StatesGroup):
    """States for editing published post."""
    
    selecting_action = State()  # Choose what to edit
    editing_text = State()  # New text input
    editing_buttons = State()  # Button management
    adding_button = State()  # Adding new button
    editing_button = State()  # Editing existing button


def edit_menu_keyboard(post_id: int) -> InlineKeyboardMarkup:
    """Build edit menu keyboard."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_text_{post_id}")],
        [InlineKeyboardButton(text="🔘 Управление кнопками", callback_data=f"edit_buttons_{post_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="edit_cancel")],
    ])


def buttons_menu_keyboard(post_id: int, buttons: list) -> InlineKeyboardMarkup:
    """Build buttons management keyboard."""
    kb = []
    
    # List existing buttons with edit option
    for i, btn in enumerate(buttons):
        kb.append([
            InlineKeyboardButton(
                text=f"📝 {btn.text[:20]}..." if len(btn.text) > 20 else f"📝 {btn.text}",
                callback_data=f"editbtn_{post_id}_{btn.id}"
            ),
            InlineKeyboardButton(
                text="🗑",
                callback_data=f"delbtn_{post_id}_{btn.id}"
            ),
        ])
    
    # Add new button option
    kb.append([InlineKeyboardButton(text="➕ Добавить кнопку", callback_data=f"addbtn_{post_id}")])
    kb.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=f"edit_back_{post_id}")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


# =============================================================================
# /edit command
# =============================================================================

@router.message(Command("edit"))
async def cmd_edit_post(message: Message, state: FSMContext) -> None:
    """Start editing a published post."""
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.answer(
            "📝 <b>Редактирование поста</b>\n\n"
            "Используйте: <code>/edit &lt;ID поста&gt;</code>\n\n"
            "ID поста показывается после публикации.\n"
            "Также можно использовать /posts для просмотра опубликованных постов."
        )
        return
    
    try:
        post_id = int(args[1])
    except ValueError:
        await message.answer("❌ Неверный ID поста. Укажите число.")
        return
    
    user_id = message.from_user.id
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await message.answer("❌ Пост не найден.")
            return
        
        if post.author_id != user_id:
            # Check if user is admin
            settings = get_settings()
            if user_id not in settings.admin_ids:
                await message.answer("❌ У вас нет прав на редактирование этого поста.")
                return
        
        if post.status != PostStatus.PUBLISHED.value:
            await message.answer(
                f"⚠️ Этот пост ещё не опубликован (статус: {post.status}).\n"
                "Редактировать можно только опубликованные посты."
            )
            return
        
        # Save post info to state
        await state.update_data(
            edit_post_id=post_id,
            edit_message_id=post.published_message_id,
        )
        await state.set_state(EditPost.selecting_action)
        
        text_preview = (post.text[:100] + "...") if post.text and len(post.text) > 100 else (post.text or "<без текста>")
        buttons_count = len(post.buttons)
        
        await message.answer(
            f"📝 <b>Редактирование поста #{post_id}</b>\n\n"
            f"<b>Текст:</b>\n<i>{text_preview}</i>\n\n"
            f"<b>Кнопок:</b> {buttons_count}\n"
            f"<b>ID сообщения:</b> <code>{post.published_message_id}</code>\n\n"
            "Выберите, что хотите изменить:",
            reply_markup=edit_menu_keyboard(post_id),
        )
        
        logger.info(f"User {user_id} started editing post {post_id}")


# =============================================================================
# Edit text
# =============================================================================

@router.callback_query(StateFilter(EditPost.selecting_action), F.data.startswith("edit_text_"))
async def start_edit_text(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing post text."""
    post_id = int(callback.data.split("_")[2])
    
    await state.update_data(edit_post_id=post_id)
    await state.set_state(EditPost.editing_text)
    
    await callback.message.edit_text(
        "✏️ <b>Редактирование текста</b>\n\n"
        "Отправьте новый текст для поста.\n\n"
        "💡 <i>Форматирование и emoji будут сохранены.</i>",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()


@router.message(StateFilter(EditPost.editing_text), F.text)
async def handle_new_text(message: Message, state: FSMContext) -> None:
    """Handle new text input."""
    from app.routers.post_wizard import entities_to_list
    
    data = await state.get_data()
    post_id = data.get("edit_post_id")
    
    new_text = message.text
    new_entities = entities_to_list(message.entities)
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post or not post.published_message_id:
            await message.answer("❌ Пост не найден или не опубликован.")
            await state.clear()
            return
        
        # Update in channel
        settings = get_settings()
        try:
            # Build keyboard from existing buttons
            keyboard = None
            if post.buttons:
                kb_rows = []
                for btn in post.buttons:
                    kb_rows.append([InlineKeyboardButton(text=btn.text, url=btn.url)])
                keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)
            
            # Check if post has media
            if post.media:
                # Edit caption for media message
                from aiogram.types import InputMediaPhoto, InputMediaVideo
                from app.routers.post_wizard import list_to_entities
                
                entities = list_to_entities(new_entities)
                
                await bot.edit_message_caption(
                    chat_id=settings.channel_id,
                    message_id=post.published_message_id,
                    caption=new_text,
                    caption_entities=entities,
                    reply_markup=keyboard,
                )
            else:
                # Edit text message
                from app.routers.post_wizard import list_to_entities
                entities = list_to_entities(new_entities)
                
                await bot.edit_message_text(
                    chat_id=settings.channel_id,
                    message_id=post.published_message_id,
                    text=new_text,
                    entities=entities,
                    reply_markup=keyboard,
                )
            
            # Update in database
            await repo.update(post_id, text=new_text, text_entities=new_entities)
            
            await message.answer(
                "✅ <b>Текст обновлён!</b>\n\n"
                f"Пост #{post_id} успешно отредактирован.",
                reply_markup=edit_menu_keyboard(post_id),
            )
            await state.set_state(EditPost.selecting_action)
            
            logger.info(f"User {message.from_user.id} updated text of post {post_id}")
            
        except Exception as e:
            logger.exception(f"Failed to edit post {post_id}: {e}")
            from html import escape
            await message.answer(
                f"❌ <b>Ошибка редактирования</b>\n\n"
                f"<code>{escape(str(e)[:200])}</code>"
            )


# =============================================================================
# Edit buttons
# =============================================================================

@router.callback_query(StateFilter(EditPost.selecting_action), F.data.startswith("edit_buttons_"))
async def start_edit_buttons(callback: CallbackQuery, state: FSMContext) -> None:
    """Show buttons management menu."""
    post_id = int(callback.data.split("_")[2])
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return
        
        await state.update_data(edit_post_id=post_id)
        await state.set_state(EditPost.editing_buttons)
        
        if post.buttons:
            buttons_text = "\n".join([f"• {btn.text} → {btn.url[:30]}..." for btn in post.buttons])
        else:
            buttons_text = "<i>Кнопок нет</i>"
        
        await callback.message.edit_text(
            f"🔘 <b>Управление кнопками</b>\n\n"
            f"<b>Текущие кнопки:</b>\n{buttons_text}\n\n"
            "Выберите действие:",
            reply_markup=buttons_menu_keyboard(post_id, list(post.buttons)),
        )
        await callback.answer()


@router.callback_query(StateFilter(EditPost.editing_buttons), F.data.startswith("addbtn_"))
async def start_add_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Start adding new button."""
    post_id = int(callback.data.split("_")[1])
    
    await state.update_data(edit_post_id=post_id)
    await state.set_state(EditPost.adding_button)
    
    await callback.message.edit_text(
        "➕ <b>Добавление кнопки</b>\n\n"
        "Отправьте кнопку в формате:\n"
        "<code>Текст кнопки - https://url.com</code>\n\n"
        "💡 <i>Можно добавить несколько кнопок, каждую на новой строке</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"edit_buttons_{post_id}")],
        ]),
    )
    await callback.answer()


@router.message(StateFilter(EditPost.adding_button), F.text)
async def handle_add_button(message: Message, state: FSMContext) -> None:
    """Handle new button input."""
    from app.utils.telegram import parse_button_text
    
    data = await state.get_data()
    post_id = data.get("edit_post_id")
    
    new_buttons = parse_button_text(message.text)
    
    if not new_buttons:
        await message.answer(
            "❌ <b>Не удалось распознать кнопку</b>\n\n"
            "Формат: <code>Текст - https://url.com</code>"
        )
        return
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        btn_repo = DraftButtonRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await message.answer("❌ Пост не найден.")
            await state.clear()
            return
        
        # Get current max row
        current_buttons = list(post.buttons)
        max_row = max([b.row for b in current_buttons], default=-1)
        
        # Add new buttons
        for i, (btn_text, btn_url) in enumerate(new_buttons):
            await btn_repo.add_button(
                post_id=post_id,
                text=btn_text,
                url=btn_url,
                row=max_row + 1 + i,
                position=0,
            )
        
        # Update message in channel
        await _update_channel_buttons(session, post_id)
        
        await message.answer(
            f"✅ Добавлено кнопок: {len(new_buttons)}",
        )
        
        # Refresh post and show buttons menu
        post = await repo.get_by_id(post_id)
        await state.set_state(EditPost.editing_buttons)
        
        await message.answer(
            "🔘 <b>Управление кнопками</b>",
            reply_markup=buttons_menu_keyboard(post_id, list(post.buttons)),
        )
        
        logger.info(f"User {message.from_user.id} added {len(new_buttons)} buttons to post {post_id}")


@router.callback_query(StateFilter(EditPost.editing_buttons), F.data.startswith("editbtn_"))
async def start_edit_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Start editing existing button."""
    parts = callback.data.split("_")
    post_id = int(parts[1])
    button_id = int(parts[2])
    
    async with get_session() as session:
        btn_repo = DraftButtonRepository(session)
        buttons = await btn_repo.get_by_post(post_id)
        button = next((b for b in buttons if b.id == button_id), None)
        
        if not button:
            await callback.answer("Кнопка не найдена", show_alert=True)
            return
        
        await state.update_data(
            edit_post_id=post_id,
            edit_button_id=button_id,
        )
        await state.set_state(EditPost.editing_button)
        
        await callback.message.edit_text(
            f"📝 <b>Редактирование кнопки</b>\n\n"
            f"<b>Текущий текст:</b> {button.text}\n"
            f"<b>Текущий URL:</b> {button.url}\n\n"
            "Отправьте новые данные в формате:\n"
            "<code>Новый текст - https://new-url.com</code>\n\n"
            "Или отправьте только URL, чтобы изменить ссылку.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="⬅️ Назад", callback_data=f"edit_buttons_{post_id}")],
            ]),
        )
        await callback.answer()


@router.message(StateFilter(EditPost.editing_button), F.text)
async def handle_edit_button(message: Message, state: FSMContext) -> None:
    """Handle button edit input."""
    from app.utils.telegram import parse_button_text
    
    data = await state.get_data()
    post_id = data.get("edit_post_id")
    button_id = data.get("edit_button_id")
    
    text = message.text.strip()
    
    # Try to parse as "text - url" format
    parsed = parse_button_text(text)
    
    if parsed:
        new_text, new_url = parsed[0]
    elif text.startswith("http://") or text.startswith("https://"):
        # Just URL - update only URL
        new_url = text
        new_text = None
    else:
        await message.answer(
            "❌ <b>Неверный формат</b>\n\n"
            "Отправьте:\n"
            "• <code>Текст - https://url.com</code> — изменить текст и URL\n"
            "• <code>https://url.com</code> — изменить только URL"
        )
        return
    
    async with get_session() as session:
        btn_repo = DraftButtonRepository(session)
        
        update_data = {"url": new_url}
        if new_text:
            update_data["text"] = new_text
        
        await btn_repo.update_button(button_id, **update_data)
        
        # Update message in channel
        await _update_channel_buttons(session, post_id)
        
        await message.answer("✅ Кнопка обновлена!")
        
        # Show buttons menu
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        await state.set_state(EditPost.editing_buttons)
        
        await message.answer(
            "🔘 <b>Управление кнопками</b>",
            reply_markup=buttons_menu_keyboard(post_id, list(post.buttons)),
        )
        
        logger.info(f"User {message.from_user.id} edited button {button_id} of post {post_id}")


@router.callback_query(StateFilter(EditPost.editing_buttons), F.data.startswith("delbtn_"))
async def delete_button(callback: CallbackQuery, state: FSMContext) -> None:
    """Delete a button."""
    parts = callback.data.split("_")
    post_id = int(parts[1])
    button_id = int(parts[2])
    
    async with get_session() as session:
        btn_repo = DraftButtonRepository(session)
        deleted = await btn_repo.delete_button(button_id)
        
        if deleted:
            # Update message in channel
            await _update_channel_buttons(session, post_id)
            await callback.answer("✅ Кнопка удалена")
        else:
            await callback.answer("❌ Кнопка не найдена", show_alert=True)
            return
        
        # Refresh buttons menu
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if post.buttons:
            buttons_text = "\n".join([f"• {btn.text} → {btn.url[:30]}..." for btn in post.buttons])
        else:
            buttons_text = "<i>Кнопок нет</i>"
        
        await callback.message.edit_text(
            f"🔘 <b>Управление кнопками</b>\n\n"
            f"<b>Текущие кнопки:</b>\n{buttons_text}\n\n"
            "Выберите действие:",
            reply_markup=buttons_menu_keyboard(post_id, list(post.buttons)),
        )
        
        logger.info(f"User {callback.from_user.id} deleted button {button_id} from post {post_id}")


# =============================================================================
# Navigation
# =============================================================================

@router.callback_query(F.data.startswith("edit_back_"))
async def back_to_edit_menu(callback: CallbackQuery, state: FSMContext) -> None:
    """Go back to edit menu."""
    post_id = int(callback.data.split("_")[2])
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            await state.clear()
            return
        
        await state.set_state(EditPost.selecting_action)
        
        text_preview = (post.text[:100] + "...") if post.text and len(post.text) > 100 else (post.text or "<без текста>")
        buttons_count = len(post.buttons)
        
        await callback.message.edit_text(
            f"📝 <b>Редактирование поста #{post_id}</b>\n\n"
            f"<b>Текст:</b>\n<i>{text_preview}</i>\n\n"
            f"<b>Кнопок:</b> {buttons_count}\n\n"
            "Выберите, что хотите изменить:",
            reply_markup=edit_menu_keyboard(post_id),
        )
        await callback.answer()


@router.callback_query(F.data == "edit_cancel")
async def cancel_edit(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel editing."""
    await state.clear()
    await callback.message.edit_text("❌ Редактирование отменено.")
    await callback.answer()


# =============================================================================
# Helper functions
# =============================================================================

async def _update_channel_buttons(session, post_id: int) -> bool:
    """Update buttons on the published message in channel."""
    repo = DraftPostRepository(session)
    post = await repo.get_by_id(post_id)
    
    if not post or not post.published_message_id:
        return False
    
    settings = get_settings()
    
    # Build new keyboard
    keyboard = None
    if post.buttons:
        kb_rows = []
        for btn in post.buttons:
            kb_rows.append([InlineKeyboardButton(text=btn.text, url=btn.url)])
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)
    
    try:
        if post.media:
            # For media messages, edit caption with new keyboard
            from app.routers.post_wizard import list_to_entities
            entities = list_to_entities(post.text_entities)
            
            await bot.edit_message_caption(
                chat_id=settings.channel_id,
                message_id=post.published_message_id,
                caption=post.text,
                caption_entities=entities,
                reply_markup=keyboard,
            )
        else:
            # For text messages
            from app.routers.post_wizard import list_to_entities
            entities = list_to_entities(post.text_entities)
            
            await bot.edit_message_text(
                chat_id=settings.channel_id,
                message_id=post.published_message_id,
                text=post.text,
                entities=entities,
                reply_markup=keyboard,
            )
        return True
    except Exception as e:
        logger.error(f"Failed to update channel buttons for post {post_id}: {e}")
        return False
