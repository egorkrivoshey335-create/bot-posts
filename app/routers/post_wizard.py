"""Post creation wizard with FSM."""

import logging
from dataclasses import dataclass
from typing import Optional, List

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery

from app.keyboards.inline import skip_keyboard, done_keyboard, cancel_keyboard

logger = logging.getLogger(__name__)

router = Router(name="post_wizard")


class PostWizard(StatesGroup):
    """States for post creation wizard."""

    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_buttons = State()
    waiting_for_schedule = State()
    confirmation = State()


@dataclass
class PostData:
    """Temporary storage for post data during wizard."""
    text: Optional[str] = None
    media_file_ids: List[str] = None
    media_type: Optional[str] = None

    def __post_init__(self):
        if self.media_file_ids is None:
            self.media_file_ids = []


# =============================================================================
# /new command - start wizard
# =============================================================================

@router.message(Command("new"))
async def cmd_new_post(message: Message, state: FSMContext) -> None:
    """Start new post creation wizard."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"User {user_id} started new post creation")

    # Clear any previous state data
    await state.clear()

    # Set state to waiting for text
    await state.set_state(PostWizard.waiting_for_text)

    # Confirm state was set
    current_state = await state.get_state()
    logger.info(f"State set to: {current_state}")

    await message.answer(
        "📝 <b>Создание нового поста</b>\n\n"
        "Отправьте текст поста или медиафайл (фото/видео/документ).\n"
        "Медиа можно отправить с подписью (caption).\n\n"
        "Для отмены используйте /cancel"
    )


# =============================================================================
# waiting_for_text state handlers
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_text), F.text)
async def handle_text_content(message: Message, state: FSMContext) -> None:
    """Handle plain text message in waiting_for_text state."""
    text = message.text
    user_id = message.from_user.id if message.from_user else "unknown"

    logger.info(f"[waiting_for_text] User {user_id} sent TEXT: {repr(text)[:100]}")

    # Save text to state
    await state.update_data(text=text, media_type=None, media_file_ids=[])

    await message.answer(
        "✅ <b>Текст поста сохранён!</b>\n\n"
        f"<blockquote>{text[:200]}{'...' if len(text) > 200 else ''}</blockquote>\n\n"
        "Теперь отправьте медиафайлы (фото/видео) или нажмите «Пропустить».",
        reply_markup=skip_keyboard("skip_media"),
    )

    await state.set_state(PostWizard.waiting_for_media)
    logger.info(f"State changed to: {await state.get_state()}")


@router.message(StateFilter(PostWizard.waiting_for_text), F.photo)
async def handle_photo_content(message: Message, state: FSMContext) -> None:
    """Handle photo message in waiting_for_text state."""
    user_id = message.from_user.id if message.from_user else "unknown"
    caption = message.caption or ""
    photo = message.photo[-1]  # Get highest resolution

    logger.info(
        f"[waiting_for_text] User {user_id} sent PHOTO | "
        f"file_id={photo.file_id[:20]}... | caption={repr(caption)[:50]}"
    )

    # Save to state
    await state.update_data(
        text=caption,
        media_type="photo",
        media_file_ids=[photo.file_id],
    )

    caption_info = f"\n<blockquote>{caption[:200]}</blockquote>" if caption else "\n<i>(без подписи)</i>"

    await message.answer(
        f"✅ <b>Фото получено!</b>{caption_info}\n\n"
        "Отправьте ещё медиафайлы для альбома или нажмите «Готово».",
        reply_markup=done_keyboard("done_media"),
    )

    await state.set_state(PostWizard.waiting_for_media)
    logger.info(f"State changed to: {await state.get_state()}")


@router.message(StateFilter(PostWizard.waiting_for_text), F.video)
async def handle_video_content(message: Message, state: FSMContext) -> None:
    """Handle video message in waiting_for_text state."""
    user_id = message.from_user.id if message.from_user else "unknown"
    caption = message.caption or ""
    video = message.video

    logger.info(
        f"[waiting_for_text] User {user_id} sent VIDEO | "
        f"file_id={video.file_id[:20]}... | caption={repr(caption)[:50]}"
    )

    # Save to state
    await state.update_data(
        text=caption,
        media_type="video",
        media_file_ids=[video.file_id],
    )

    caption_info = f"\n<blockquote>{caption[:200]}</blockquote>" if caption else "\n<i>(без подписи)</i>"

    await message.answer(
        f"✅ <b>Видео получено!</b>{caption_info}\n\n"
        "Отправьте ещё медиафайлы для альбома или нажмите «Готово».",
        reply_markup=done_keyboard("done_media"),
    )

    await state.set_state(PostWizard.waiting_for_media)
    logger.info(f"State changed to: {await state.get_state()}")


@router.message(StateFilter(PostWizard.waiting_for_text), F.document)
async def handle_document_content(message: Message, state: FSMContext) -> None:
    """Handle document message in waiting_for_text state."""
    user_id = message.from_user.id if message.from_user else "unknown"
    caption = message.caption or ""
    document = message.document

    logger.info(
        f"[waiting_for_text] User {user_id} sent DOCUMENT | "
        f"file_id={document.file_id[:20]}... | "
        f"file_name={document.file_name} | caption={repr(caption)[:50]}"
    )

    # Save to state
    await state.update_data(
        text=caption,
        media_type="document",
        media_file_ids=[document.file_id],
    )

    caption_info = f"\n<blockquote>{caption[:200]}</blockquote>" if caption else "\n<i>(без подписи)</i>"

    await message.answer(
        f"✅ <b>Документ получен!</b>\n"
        f"📎 {document.file_name or 'файл'}{caption_info}\n\n"
        "Отправьте ещё медиафайлы или нажмите «Готово».",
        reply_markup=done_keyboard("done_media"),
    )

    await state.set_state(PostWizard.waiting_for_media)
    logger.info(f"State changed to: {await state.get_state()}")


@router.message(StateFilter(PostWizard.waiting_for_text), F.animation)
async def handle_animation_content(message: Message, state: FSMContext) -> None:
    """Handle animation (GIF) message in waiting_for_text state."""
    user_id = message.from_user.id if message.from_user else "unknown"
    caption = message.caption or ""
    animation = message.animation

    logger.info(
        f"[waiting_for_text] User {user_id} sent ANIMATION | "
        f"file_id={animation.file_id[:20]}... | caption={repr(caption)[:50]}"
    )

    await state.update_data(
        text=caption,
        media_type="animation",
        media_file_ids=[animation.file_id],
    )

    caption_info = f"\n<blockquote>{caption[:200]}</blockquote>" if caption else "\n<i>(без подписи)</i>"

    await message.answer(
        f"✅ <b>GIF получен!</b>{caption_info}\n\n"
        "Нажмите «Готово» для продолжения.",
        reply_markup=done_keyboard("done_media"),
    )

    await state.set_state(PostWizard.waiting_for_media)
    logger.info(f"State changed to: {await state.get_state()}")


# =============================================================================
# waiting_for_media state handlers
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_media), F.photo)
async def handle_additional_photo(message: Message, state: FSMContext) -> None:
    """Handle additional photo in waiting_for_media state."""
    photo = message.photo[-1]
    data = await state.get_data()

    media_file_ids = data.get("media_file_ids", [])
    media_file_ids.append(photo.file_id)

    await state.update_data(media_file_ids=media_file_ids)

    logger.info(f"[waiting_for_media] Added photo, total media: {len(media_file_ids)}")

    await message.answer(
        f"📎 Добавлено фото (всего: {len(media_file_ids)})\n"
        "Отправьте ещё или нажмите «Готово».",
        reply_markup=done_keyboard("done_media"),
    )


@router.message(StateFilter(PostWizard.waiting_for_media), F.video)
async def handle_additional_video(message: Message, state: FSMContext) -> None:
    """Handle additional video in waiting_for_media state."""
    video = message.video
    data = await state.get_data()

    media_file_ids = data.get("media_file_ids", [])
    media_file_ids.append(video.file_id)

    await state.update_data(media_file_ids=media_file_ids)

    logger.info(f"[waiting_for_media] Added video, total media: {len(media_file_ids)}")

    await message.answer(
        f"📎 Добавлено видео (всего: {len(media_file_ids)})\n"
        "Отправьте ещё или нажмите «Готово».",
        reply_markup=done_keyboard("done_media"),
    )


@router.callback_query(StateFilter(PostWizard.waiting_for_media), F.data == "skip_media")
async def skip_media_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip media step."""
    logger.info(f"[waiting_for_media] User skipped media step")

    await callback.message.edit_text(
        "⏭ Медиа пропущено.\n\n"
        "Теперь добавьте инлайн-кнопки.\n"
        "Формат: <code>Текст кнопки - https://url.com</code>\n"
        "Каждая кнопка на новой строке.\n\n"
        "Или нажмите «Пропустить».",
        reply_markup=skip_keyboard("skip_buttons"),
    )
    await callback.answer()

    await state.set_state(PostWizard.waiting_for_buttons)


@router.callback_query(StateFilter(PostWizard.waiting_for_media), F.data == "done_media")
async def done_media_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Finish media step."""
    data = await state.get_data()
    media_count = len(data.get("media_file_ids", []))

    logger.info(f"[waiting_for_media] User finished media step with {media_count} files")

    await callback.message.edit_text(
        f"✅ Медиа сохранено ({media_count} файл(ов)).\n\n"
        "Теперь добавьте инлайн-кнопки.\n"
        "Формат: <code>Текст кнопки - https://url.com</code>\n"
        "Каждая кнопка на новой строке.\n\n"
        "Или нажмите «Пропустить».",
        reply_markup=skip_keyboard("skip_buttons"),
    )
    await callback.answer()

    await state.set_state(PostWizard.waiting_for_buttons)


# =============================================================================
# waiting_for_buttons state handlers
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_buttons), F.text)
async def handle_buttons_input(message: Message, state: FSMContext) -> None:
    """Handle button definitions input."""
    from app.utils.telegram import parse_button_text

    text = message.text
    buttons = parse_button_text(text)

    logger.info(f"[waiting_for_buttons] Parsed {len(buttons)} buttons from input")

    if not buttons:
        await message.answer(
            "❌ Не удалось распознать кнопки.\n\n"
            "Используйте формат:\n"
            "<code>Текст кнопки - https://url.com</code>\n\n"
            "Или нажмите «Пропустить».",
            reply_markup=skip_keyboard("skip_buttons"),
        )
        return

    await state.update_data(buttons=buttons)

    buttons_preview = "\n".join([f"• {btn[0]} → {btn[1]}" for btn in buttons])

    await message.answer(
        f"✅ Кнопки добавлены:\n{buttons_preview}\n\n"
        "Теперь выберите время публикации.\n"
        "Напишите время или «сейчас» для немедленной публикации.",
        reply_markup=cancel_keyboard(),
    )

    await state.set_state(PostWizard.waiting_for_schedule)


@router.callback_query(StateFilter(PostWizard.waiting_for_buttons), F.data == "skip_buttons")
async def skip_buttons_step(callback: CallbackQuery, state: FSMContext) -> None:
    """Skip buttons step."""
    logger.info(f"[waiting_for_buttons] User skipped buttons step")

    await state.update_data(buttons=[])

    await callback.message.edit_text(
        "⏭ Кнопки пропущены.\n\n"
        "Теперь выберите время публикации.\n"
        "Напишите время (например, <code>15:30</code> или <code>завтра 12:00</code>)\n"
        "или <code>сейчас</code> для немедленной публикации.",
        reply_markup=cancel_keyboard(),
    )
    await callback.answer()

    await state.set_state(PostWizard.waiting_for_schedule)


# =============================================================================
# waiting_for_schedule state handlers
# =============================================================================

@router.message(StateFilter(PostWizard.waiting_for_schedule), F.text)
async def handle_schedule_input(message: Message, state: FSMContext) -> None:
    """Handle schedule time input."""
    from app.services.datetime_parse import parse_datetime, format_datetime

    text = message.text
    parsed_dt, error = parse_datetime(text)

    if error:
        await message.answer(error, reply_markup=cancel_keyboard())
        return

    logger.info(f"[waiting_for_schedule] Parsed datetime: {parsed_dt}")

    await state.update_data(scheduled_at=parsed_dt.isoformat() if parsed_dt else None)

    # Show summary
    data = await state.get_data()
    post_text = data.get("text", "")[:100]
    media_count = len(data.get("media_file_ids", []))
    buttons_count = len(data.get("buttons", []))

    schedule_str = format_datetime(parsed_dt) if text.lower() not in ("сейчас", "now") else "немедленно"

    await message.answer(
        "📋 <b>Сводка поста:</b>\n\n"
        f"📝 Текст: {post_text}{'...' if len(data.get('text', '')) > 100 else ''}\n"
        f"🖼 Медиа: {media_count} файл(ов)\n"
        f"🔘 Кнопок: {buttons_count}\n"
        f"⏰ Публикация: {schedule_str}\n\n"
        "<i>Функция сохранения в БД будет добавлена позже.</i>",
    )

    # Clear state for now
    await state.clear()
    logger.info("[waiting_for_schedule] Wizard completed (placeholder)")


# =============================================================================
# Cancel button handler
# =============================================================================

@router.callback_query(F.data == "cancel")
async def cancel_wizard(callback: CallbackQuery, state: FSMContext) -> None:
    """Cancel the wizard from inline button."""
    await state.clear()
    await callback.message.edit_text("❌ Создание поста отменено.")
    await callback.answer()
    logger.info(f"User cancelled wizard via inline button")
