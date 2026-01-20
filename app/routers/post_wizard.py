"""Post creation wizard with FSM."""

import logging
from datetime import datetime, timezone
from typing import Optional, List, Tuple

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    MessageEntity,
)

from app.bot import bot
from app.keyboards.inline import cancel_keyboard
from app.db.models import PostStatus
from app.db.repo import create_post_with_relations, DraftPostRepository
from app.db.session import get_session
from app.services.publishing import publish_post
from app.services.scheduler import schedule_post

logger = logging.getLogger(__name__)

router = Router(name="post_wizard")


class PostWizard(StatesGroup):
    """States for post creation wizard."""

    waiting_for_content = State()  # Text or media with caption
    waiting_for_more_media = State()  # Additional media for album
    waiting_for_buttons = State()  # Inline buttons
    waiting_for_schedule = State()  # Publication time
    confirmation = State()


# =============================================================================
# Helper functions
# =============================================================================

def wizard_keyboard(
    next_step: str = None,
    show_skip: bool = False,
    show_done: bool = False,
    show_preview: bool = False,
) -> InlineKeyboardMarkup:
    """Build wizard navigation keyboard."""
    buttons = []

    if show_preview:
        buttons.append([InlineKeyboardButton(text="👁 Превью", callback_data="wizard_preview")])

    row = []
    if show_skip:
        row.append(InlineKeyboardButton(text="⏭ Пропустить", callback_data=f"wizard_skip_{next_step}"))
    if show_done:
        row.append(InlineKeyboardButton(text="✅ Готово", callback_data=f"wizard_done_{next_step}"))
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="wizard_cancel")])

    return InlineKeyboardMarkup(inline_keyboard=buttons)


def entities_to_list(entities: Optional[tuple]) -> Optional[List[dict]]:
    """Convert MessageEntity tuple to serializable list for FSM storage."""
    if not entities:
        return None
    result = []
    for entity in entities:
        result.append({
            "type": entity.type,
            "offset": entity.offset,
            "length": entity.length,
            "url": entity.url,
            "user": entity.user.model_dump() if entity.user else None,
            "language": entity.language,
            "custom_emoji_id": entity.custom_emoji_id,
        })
    return result


def list_to_entities(data: Optional[List[dict]]) -> Optional[List[MessageEntity]]:
    """Convert serialized list back to MessageEntity objects."""
    if not data:
        return None
    result = []
    for item in data:
        result.append(MessageEntity(
            type=item["type"],
            offset=item["offset"],
            length=item["length"],
            url=item.get("url"),
            language=item.get("language"),
            custom_emoji_id=item.get("custom_emoji_id"),
        ))
    return result


async def send_post_preview(
    chat_id: int,
    text: Optional[str],
    text_entities: Optional[List[dict]],
    media_file_ids: List[str],
    media_type: Optional[str],
    buttons: List[Tuple[str, str]],
) -> Optional[Message]:
    """Send actual post preview to user with preserved entities (custom emoji)."""
    # Build inline keyboard from buttons
    keyboard = None
    if buttons:
        kb_rows = []
        for btn_text, btn_url in buttons:
            kb_rows.append([InlineKeyboardButton(text=btn_text, url=btn_url)])
        keyboard = InlineKeyboardMarkup(inline_keyboard=kb_rows)

    # Convert entities from stored format
    entities = list_to_entities(text_entities)

    try:
        # No media - text only
        if not media_file_ids:
            if text:
                return await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    entities=entities,
                    reply_markup=keyboard,
                )
            return None

        # Single media
        if len(media_file_ids) == 1:
            file_id = media_file_ids[0]

            # For methods that use specific parameter name
            if media_type == "photo":
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=text,
                    caption_entities=entities,
                    reply_markup=keyboard,
                )
            elif media_type == "video":
                return await bot.send_video(
                    chat_id=chat_id,
                    video=file_id,
                    caption=text,
                    caption_entities=entities,
                    reply_markup=keyboard,
                )
            elif media_type == "document":
                return await bot.send_document(
                    chat_id=chat_id,
                    document=file_id,
                    caption=text,
                    caption_entities=entities,
                    reply_markup=keyboard,
                )
            elif media_type == "animation":
                return await bot.send_animation(
                    chat_id=chat_id,
                    animation=file_id,
                    caption=text,
                    caption_entities=entities,
                    reply_markup=keyboard,
                )
            else:
                return await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=text,
                    caption_entities=entities,
                    reply_markup=keyboard,
                )

        # Multiple media - media group (buttons sent separately)
        from aiogram.types import InputMediaPhoto, InputMediaVideo

        media_list = []
        for i, file_id in enumerate(media_file_ids):
            caption = text if i == 0 else None
            caption_ent = entities if i == 0 else None
            if media_type == "video":
                media_list.append(InputMediaVideo(
                    media=file_id,
                    caption=caption,
                    caption_entities=caption_ent,
                ))
            else:
                media_list.append(InputMediaPhoto(
                    media=file_id,
                    caption=caption,
                    caption_entities=caption_ent,
                ))

        messages = await bot.send_media_group(chat_id=chat_id, media=media_list)

        # Send buttons separately
        if keyboard:
            await bot.send_message(
                chat_id=chat_id,
                text="👆 <i>Кнопки будут прикреплены к посту</i>",
                reply_markup=keyboard,
            )

        return messages[0] if messages else None

    except Exception as e:
        logger.error(f"Failed to send preview: {e}")
        return None


# =============================================================================
# /new command - start wizard
# =============================================================================

@router.message(Command("new"))
async def cmd_new_post(message: Message, state: FSMContext) -> None:
    """Start new post creation wizard."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"User {user_id} started new post creation")

    await state.clear()
    await state.set_state(PostWizard.waiting_for_content)

    await message.answer(
        "📝 <b>Создание нового поста</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>Шаг 1 из 4: Контент</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Отправьте контент для поста:\n\n"
        "• <b>Текст</b> — просто напишите сообщение\n"
        "• <b>Фото/Видео</b> — отправьте медиафайл\n"
        "• <b>Фото + текст</b> — добавьте подпись к медиа\n\n"
        "💡 <i>Подпись (caption) к фото/видео станет текстом поста</i>\n"
        "💡 <i>Premium emoji в тексте сохраняются</i>",
        reply_markup=cancel_keyboard(),
    )


# =============================================================================
# Step 1: Content (text / media with caption)
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_content), F.text)
async def handle_text_content(message: Message, state: FSMContext) -> None:
    """Handle plain text message."""
    text = message.text
    entities = entities_to_list(message.entities)
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"[content] User {user_id} sent text: {repr(text)[:50]}, entities: {len(message.entities or [])}")

    await state.update_data(
        text=text,
        text_entities=entities,
        media_type=None,
        media_file_ids=[],
        buttons=[],
    )

    # Show preview
    await message.answer("👁 <b>Превью поста:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=text,
        text_entities=entities,
        media_file_ids=[],
        media_type=None,
        buttons=[],
    )

    await _ask_for_buttons(message, state)


@router.message(StateFilter(PostWizard.waiting_for_content), F.photo)
async def handle_photo_content(message: Message, state: FSMContext) -> None:
    """Handle photo message."""
    user_id = message.from_user.id if message.from_user else "unknown"
    caption = message.caption or ""
    caption_entities = entities_to_list(message.caption_entities)
    photo = message.photo[-1]

    logger.info(f"[content] User {user_id} sent photo with caption: {repr(caption)[:50]}, entities: {len(message.caption_entities or [])}")

    await state.update_data(
        text=caption,
        text_entities=caption_entities,
        media_type="photo",
        media_file_ids=[photo.file_id],
        buttons=[],
    )

    # Show preview
    await message.answer("👁 <b>Превью поста:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=caption,
        text_entities=caption_entities,
        media_file_ids=[photo.file_id],
        media_type="photo",
        buttons=[],
    )

    await _ask_for_more_media(message, state)


@router.message(StateFilter(PostWizard.waiting_for_content), F.video)
async def handle_video_content(message: Message, state: FSMContext) -> None:
    """Handle video message."""
    caption = message.caption or ""
    caption_entities = entities_to_list(message.caption_entities)
    video = message.video

    await state.update_data(
        text=caption,
        text_entities=caption_entities,
        media_type="video",
        media_file_ids=[video.file_id],
        buttons=[],
    )

    await message.answer("👁 <b>Превью поста:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=caption,
        text_entities=caption_entities,
        media_file_ids=[video.file_id],
        media_type="video",
        buttons=[],
    )

    await _ask_for_more_media(message, state)


@router.message(StateFilter(PostWizard.waiting_for_content), F.document)
async def handle_document_content(message: Message, state: FSMContext) -> None:
    """Handle document message."""
    caption = message.caption or ""
    caption_entities = entities_to_list(message.caption_entities)
    document = message.document

    await state.update_data(
        text=caption,
        text_entities=caption_entities,
        media_type="document",
        media_file_ids=[document.file_id],
        buttons=[],
    )

    await message.answer("👁 <b>Превью поста:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=caption,
        text_entities=caption_entities,
        media_file_ids=[document.file_id],
        media_type="document",
        buttons=[],
    )

    # Documents don't support albums, go to buttons
    await _ask_for_buttons(message, state)


@router.message(StateFilter(PostWizard.waiting_for_content), F.animation)
async def handle_animation_content(message: Message, state: FSMContext) -> None:
    """Handle animation (GIF) message."""
    caption = message.caption or ""
    caption_entities = entities_to_list(message.caption_entities)
    animation = message.animation

    await state.update_data(
        text=caption,
        text_entities=caption_entities,
        media_type="animation",
        media_file_ids=[animation.file_id],
        buttons=[],
    )

    await message.answer("👁 <b>Превью поста:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=caption,
        text_entities=caption_entities,
        media_file_ids=[animation.file_id],
        media_type="animation",
        buttons=[],
    )

    # Animations don't support albums, go to buttons
    await _ask_for_buttons(message, state)


async def _ask_for_more_media(message: Message, state: FSMContext) -> None:
    """Ask user for additional media."""
    await state.set_state(PostWizard.waiting_for_more_media)

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>Шаг 2 из 4: Альбом</b> (опционально)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Хотите добавить ещё фото/видео в альбом?\n\n"
        "• Отправьте ещё медиафайлы\n"
        "• Или нажмите <b>«Готово»</b> чтобы продолжить\n\n"
        "💡 <i>В альбоме может быть до 10 медиафайлов</i>",
        reply_markup=wizard_keyboard(next_step="media", show_done=True),
    )


async def _ask_for_buttons(message: Message, state: FSMContext) -> None:
    """Ask user for inline buttons."""
    await state.set_state(PostWizard.waiting_for_buttons)

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>Шаг 3 из 4: Кнопки</b> (опционально)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Добавьте инлайн-кнопки со ссылками.\n\n"
        "<b>Формат:</b>\n"
        "<code>Текст кнопки - https://example.com</code>\n\n"
        "<b>Пример:</b>\n"
        "<code>Наш сайт - https://mysite.com</code>\n"
        "<code>Telegram - https://t.me/channel</code>\n\n"
        "💡 <i>Каждая кнопка на новой строке</i>\n"
        "💡 <i>Можно отправить несколько кнопок одним сообщением</i>",
        reply_markup=wizard_keyboard(next_step="buttons", show_skip=True),
    )


# =============================================================================
# Step 2: Additional media (album)
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_more_media), F.photo)
async def handle_additional_photo(message: Message, state: FSMContext) -> None:
    """Handle additional photo for album."""
    photo = message.photo[-1]
    data = await state.get_data()

    media_file_ids = data.get("media_file_ids", [])
    media_file_ids.append(photo.file_id)

    await state.update_data(media_file_ids=media_file_ids)
    logger.info(f"[more_media] Added photo, total: {len(media_file_ids)}")

    # Show updated preview
    await message.answer(f"✅ Добавлено фото #{len(media_file_ids)}\n\n👁 <b>Превью альбома:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=data.get("text", ""),
        text_entities=data.get("text_entities"),
        media_file_ids=media_file_ids,
        media_type="photo",
        buttons=[],
    )

    if len(media_file_ids) >= 10:
        await message.answer("📎 Достигнут лимит в 10 медиафайлов.")
        await _ask_for_buttons(message, state)
    else:
        await message.answer(
            f"📎 Всего в альбоме: {len(media_file_ids)} файл(ов)\n"
            "Отправьте ещё или нажмите «Готово».",
            reply_markup=wizard_keyboard(next_step="media", show_done=True),
        )


@router.message(StateFilter(PostWizard.waiting_for_more_media), F.video)
async def handle_additional_video(message: Message, state: FSMContext) -> None:
    """Handle additional video for album."""
    video = message.video
    data = await state.get_data()

    media_file_ids = data.get("media_file_ids", [])
    media_file_ids.append(video.file_id)

    await state.update_data(media_file_ids=media_file_ids, media_type="video")
    logger.info(f"[more_media] Added video, total: {len(media_file_ids)}")

    await message.answer(f"✅ Добавлено видео #{len(media_file_ids)}")

    if len(media_file_ids) >= 10:
        await _ask_for_buttons(message, state)
    else:
        await message.answer(
            f"📎 Всего в альбоме: {len(media_file_ids)} файл(ов)\n"
            "Отправьте ещё или нажмите «Готово».",
            reply_markup=wizard_keyboard(next_step="media", show_done=True),
        )


@router.callback_query(StateFilter(PostWizard.waiting_for_more_media), F.data == "wizard_done_media")
async def done_media_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Finish adding media."""
    await callback.message.delete()
    await callback.answer()
    await _ask_for_buttons(callback.message, state)


# =============================================================================
# Step 3: Buttons
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_buttons), F.text)
async def handle_buttons_input(message: Message, state: FSMContext) -> None:
    """Handle button definitions."""
    from app.utils.telegram import parse_button_text

    text = message.text
    new_buttons = parse_button_text(text)

    if not new_buttons:
        await message.answer(
            "❌ <b>Не удалось распознать кнопки</b>\n\n"
            "Проверьте формат:\n"
            "<code>Текст кнопки - https://example.com</code>\n\n"
            "Разделитель: <code> - </code> (пробел-дефис-пробел)\n\n"
            "Попробуйте ещё раз или нажмите «Пропустить».",
            reply_markup=wizard_keyboard(next_step="buttons", show_skip=True),
        )
        return

    # Add to existing buttons
    data = await state.get_data()
    buttons = data.get("buttons", [])
    buttons.extend(new_buttons)
    await state.update_data(buttons=buttons)

    logger.info(f"[buttons] Added {len(new_buttons)} buttons, total: {len(buttons)}")

    # Show preview with buttons
    await message.answer(f"✅ Добавлено кнопок: {len(new_buttons)}\n\n👁 <b>Превью поста с кнопками:</b>")
    await send_post_preview(
        chat_id=message.chat.id,
        text=data.get("text", ""),
        text_entities=data.get("text_entities"),
        media_file_ids=data.get("media_file_ids", []),
        media_type=data.get("media_type"),
        buttons=buttons,
    )

    await message.answer(
        f"🔘 Всего кнопок: {len(buttons)}\n\n"
        "Отправьте ещё кнопки или нажмите «Готово».",
        reply_markup=wizard_keyboard(next_step="buttons", show_done=True),
    )


@router.callback_query(StateFilter(PostWizard.waiting_for_buttons), F.data == "wizard_skip_buttons")
async def skip_buttons_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip buttons step."""
    await callback.message.delete()
    await callback.answer()
    await _ask_for_schedule(callback.message, state)


@router.callback_query(StateFilter(PostWizard.waiting_for_buttons), F.data == "wizard_done_buttons")
async def done_buttons_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Finish adding buttons."""
    await callback.message.delete()
    await callback.answer()
    await _ask_for_schedule(callback.message, state)


async def _ask_for_schedule(message: Message, state: FSMContext) -> None:
    """Ask user for publication time."""
    await state.set_state(PostWizard.waiting_for_schedule)

    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 <b>Шаг 4 из 4: Время публикации</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Когда опубликовать пост?\n\n"
        "<b>Примеры форматов:</b>\n"
        "• <code>сейчас</code> — немедленная публикация\n"
        "• <code>15:30</code> — сегодня в 15:30\n"
        "• <code>завтра 15:30</code> — завтра в 15:30\n"
        "• <code>25.01 15:30</code> — 25 января в 15:30\n"
        "• <code>25.01.2025 15:30</code> — конкретная дата\n\n"
        "💡 <i>Время указывается по часовому поясу из настроек бота</i>",
        reply_markup=cancel_keyboard(),
    )


# =============================================================================
# Step 4: Schedule
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_schedule), F.text)
async def handle_schedule_input(message: Message, state: FSMContext) -> None:
    """Handle schedule time input."""
    from app.services.datetime_parse import parse_datetime, format_datetime

    text = message.text.strip()
    parsed_dt, error = parse_datetime(text)

    if error:
        await message.answer(
            f"{error}\n\n"
            "<b>Примеры:</b>\n"
            "• <code>сейчас</code>\n"
            "• <code>15:30</code>\n"
            "• <code>завтра 12:00</code>\n"
            "• <code>25.01 18:00</code>",
            reply_markup=cancel_keyboard(),
        )
        return

    is_immediate = text.lower() in ("сейчас", "now", "немедленно")
    schedule_str = "немедленно" if is_immediate else format_datetime(parsed_dt)

    await state.update_data(scheduled_at=parsed_dt.isoformat() if parsed_dt else None)

    data = await state.get_data()

    # Final preview
    await message.answer(
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "✅ <b>Пост готов к публикации!</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👁 <b>Финальное превью:</b>"
    )

    await send_post_preview(
        chat_id=message.chat.id,
        text=data.get("text", ""),
        text_entities=data.get("text_entities"),
        media_file_ids=data.get("media_file_ids", []),
        media_type=data.get("media_type"),
        buttons=data.get("buttons", []),
    )

    media_count = len(data.get("media_file_ids", []))
    buttons_count = len(data.get("buttons", []))

    # Choose button text based on schedule
    publish_text = "📤 Опубликовать сейчас" if is_immediate else "📤 Запланировать"
    
    await message.answer(
        f"📋 <b>Параметры:</b>\n"
        f"• Медиа: {media_count} файл(ов)\n"
        f"• Кнопок: {buttons_count}\n"
        f"• Публикация: {schedule_str}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=publish_text, callback_data="wizard_publish")],
            [InlineKeyboardButton(text="💾 Сохранить черновик", callback_data="wizard_save_draft")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="wizard_cancel")],
        ]),
    )

    await state.set_state(PostWizard.confirmation)


# =============================================================================
# Confirmation & Cancel
# =============================================================================

@router.callback_query(F.data == "wizard_cancel")
async def cancel_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the wizard."""
    await state.clear()
    await callback.message.edit_text("❌ Создание поста отменено.")
    await callback.answer()


@router.callback_query(StateFilter(PostWizard.confirmation), F.data == "wizard_publish")
async def publish_immediately(callback: CallbackQuery, state: FSMContext) -> None:
    """Publish post immediately or schedule it."""
    await callback.answer("⏳ Обрабатываю...")
    
    user = callback.from_user
    data = await state.get_data()
    
    # Parse scheduled_at
    scheduled_at_str = data.get("scheduled_at")
    scheduled_at = None
    if scheduled_at_str:
        try:
            scheduled_at = datetime.fromisoformat(scheduled_at_str)
        except (ValueError, TypeError):
            pass
    
    # Determine if immediate or scheduled
    is_immediate = scheduled_at is None or scheduled_at <= datetime.now(timezone.utc)
    
    # Prepare media items
    media_items = None
    media_file_ids = data.get("media_file_ids", [])
    media_type = data.get("media_type")
    if media_file_ids and media_type:
        media_items = [
            {"file_id": fid, "file_unique_id": fid, "media_type": media_type}
            for fid in media_file_ids
        ]
    
    try:
        async with get_session() as session:
            # Create post in DB
            post = await create_post_with_relations(
                session=session,
                author_id=user.id,
                author_username=user.username,
                text=data.get("text"),
                text_entities=data.get("text_entities"),
                media_items=media_items,
                buttons=data.get("buttons"),
                scheduled_at=scheduled_at if not is_immediate else None,
                status=PostStatus.SCHEDULED if not is_immediate else PostStatus.DRAFT,
            )
            
            if is_immediate:
                # Publish now
                message_id = await publish_post(post)
                
                if message_id:
                    # Update post status
                    repo = DraftPostRepository(session)
                    await repo.mark_published(
                        post_id=post.id,
                        message_id=message_id,
                        published_at=datetime.now(timezone.utc),
                    )
                    
                    await callback.message.edit_text(
                        "✅ <b>Пост успешно опубликован!</b>\n\n"
                        f"📝 ID поста: <code>{post.id}</code>\n"
                        f"📨 ID сообщения: <code>{message_id}</code>"
                    )
                    logger.info(f"User {user.id} published post {post.id}, message_id={message_id}")
                else:
                    await repo.mark_failed(post.id)
                    await callback.message.edit_text(
                        "❌ <b>Ошибка публикации</b>\n\n"
                        "Не удалось отправить пост в канал. "
                        "Проверьте, что бот является администратором канала."
                    )
                    logger.error(f"Failed to publish post {post.id} for user {user.id}")
            else:
                # Schedule for later
                job_id = await schedule_post(post.id, scheduled_at)
                
                # Update job ID in DB
                repo = DraftPostRepository(session)
                await repo.update(post.id, scheduler_job_id=job_id)
                
                from app.services.datetime_parse import format_datetime
                await callback.message.edit_text(
                    "✅ <b>Пост запланирован!</b>\n\n"
                    f"📝 ID поста: <code>{post.id}</code>\n"
                    f"📅 Публикация: {format_datetime(scheduled_at)}\n\n"
                    "💡 <i>Используйте /drafts для управления черновиками</i>"
                )
                logger.info(f"User {user.id} scheduled post {post.id} for {scheduled_at}")
    
    except Exception as e:
        logger.exception(f"Error publishing post for user {user.id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            "Попробуйте ещё раз или обратитесь к администратору."
        )
    
    await state.clear()


@router.callback_query(StateFilter(PostWizard.confirmation), F.data == "wizard_save_draft")
async def save_as_draft(callback: CallbackQuery, state: FSMContext) -> None:
    """Save post as draft without publishing."""
    await callback.answer("⏳ Сохраняю...")
    
    user = callback.from_user
    data = await state.get_data()
    
    # Prepare media items
    media_items = None
    media_file_ids = data.get("media_file_ids", [])
    media_type = data.get("media_type")
    if media_file_ids and media_type:
        media_items = [
            {"file_id": fid, "file_unique_id": fid, "media_type": media_type}
            for fid in media_file_ids
        ]
    
    try:
        async with get_session() as session:
            # Create draft post in DB
            post = await create_post_with_relations(
                session=session,
                author_id=user.id,
                author_username=user.username,
                text=data.get("text"),
                text_entities=data.get("text_entities"),
                media_items=media_items,
                buttons=data.get("buttons"),
                status=PostStatus.DRAFT,
            )
            
            await callback.message.edit_text(
                "✅ <b>Черновик сохранён!</b>\n\n"
                f"📝 ID поста: <code>{post.id}</code>\n\n"
                "💡 <i>Используйте /drafts для управления черновиками</i>"
            )
            logger.info(f"User {user.id} saved draft {post.id}")
    
    except Exception as e:
        logger.exception(f"Error saving draft for user {user.id}: {e}")
        await callback.message.edit_text(
            "❌ <b>Произошла ошибка при сохранении</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            "Попробуйте ещё раз или обратитесь к администратору."
        )
    
    await state.clear()
