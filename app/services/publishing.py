"""Publishing service for sending posts to channel."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    InputMediaVideo,
    InputMediaDocument,
    InputMediaAudio,
    InputMediaAnimation,
)

from app.bot import bot
from app.config import get_settings
from app.db.models import DraftPost, DraftButton, DraftMedia, MediaType, PostStatus
from app.db.repo import DraftPostRepository
from app.db.session import get_session

logger = logging.getLogger(__name__)


def build_keyboard(buttons: List[DraftButton]) -> Optional[InlineKeyboardMarkup]:
    """Build inline keyboard from button list."""
    if not buttons:
        return None
    
    # Group buttons by row
    rows: dict[int, List[InlineKeyboardButton]] = {}
    for btn in buttons:
        if btn.row not in rows:
            rows[btn.row] = []
        rows[btn.row].append(
            InlineKeyboardButton(text=btn.text, url=btn.url)
        )
    
    # Build keyboard from rows
    keyboard = []
    for row_num in sorted(rows.keys()):
        keyboard.append(rows[row_num])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_input_media(media: DraftMedia, caption: Optional[str] = None):
    """Convert DraftMedia to appropriate InputMedia type."""
    media_classes = {
        MediaType.PHOTO.value: InputMediaPhoto,
        MediaType.VIDEO.value: InputMediaVideo,
        MediaType.DOCUMENT.value: InputMediaDocument,
        MediaType.AUDIO.value: InputMediaAudio,
        MediaType.ANIMATION.value: InputMediaAnimation,
    }
    
    media_class = media_classes.get(media.media_type, InputMediaPhoto)
    return media_class(media=media.file_id, caption=caption)


async def publish_post(post: DraftPost) -> Optional[int]:
    """
    Publish a post to the channel.
    
    Args:
        post: Draft post to publish
        
    Returns:
        Message ID of the published message, or None if failed
    """
    settings = get_settings()
    channel_id = settings.channel_id
    
    keyboard = build_keyboard(list(post.buttons))
    
    try:
        # Case 1: No media, text only
        if not post.media:
            message = await bot.send_message(
                chat_id=channel_id,
                text=post.text or "",
                reply_markup=keyboard,
                disable_web_page_preview=post.disable_link_preview,
                disable_notification=post.disable_notification,
            )
            return message.message_id
        
        # Case 2: Single media
        if len(post.media) == 1:
            media = post.media[0]
            send_methods = {
                MediaType.PHOTO.value: bot.send_photo,
                MediaType.VIDEO.value: bot.send_video,
                MediaType.DOCUMENT.value: bot.send_document,
                MediaType.AUDIO.value: bot.send_audio,
                MediaType.ANIMATION.value: bot.send_animation,
            }
            
            send_method = send_methods.get(media.media_type, bot.send_photo)
            message = await send_method(
                chat_id=channel_id,
                **{media.media_type: media.file_id},
                caption=post.text,
                reply_markup=keyboard,
                disable_notification=post.disable_notification,
            )
            return message.message_id
        
        # Case 3: Media group (album)
        media_list = []
        for i, media in enumerate(post.media):
            # Only first media has caption
            caption = post.text if i == 0 else None
            media_list.append(get_input_media(media, caption))
        
        messages = await bot.send_media_group(
            chat_id=channel_id,
            media=media_list,
            disable_notification=post.disable_notification,
        )
        
        # For media groups, return first message ID
        # Note: Inline buttons are not supported in media groups
        return messages[0].message_id if messages else None
        
    except Exception as e:
        logger.error(f"Failed to publish post {post.id}: {e}")
        return None


async def publish_scheduled_post(post_id: int) -> None:
    """
    Publish a scheduled post (called by APScheduler).
    
    Args:
        post_id: ID of the post to publish
    """
    logger.info(f"Publishing scheduled post {post_id}")
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            logger.error(f"Post {post_id} not found")
            return
        
        if post.status != PostStatus.SCHEDULED.value:
            logger.warning(f"Post {post_id} is not in scheduled status")
            return
        
        message_id = await publish_post(post)
        
        if message_id:
            await repo.mark_published(
                post_id=post_id,
                message_id=message_id,
                published_at=datetime.now(timezone.utc),
            )
            logger.info(f"Post {post_id} published successfully, message_id={message_id}")
        else:
            await repo.mark_failed(post_id)
            logger.error(f"Post {post_id} publication failed")
