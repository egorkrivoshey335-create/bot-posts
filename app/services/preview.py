"""Preview service for rendering posts in DM."""

import logging
from typing import Optional

from aiogram.types import Message

from app.bot import bot
from app.db.models import DraftPost
from app.services.publishing import build_keyboard, get_input_media

logger = logging.getLogger(__name__)


async def send_preview(
    chat_id: int,
    post: DraftPost,
    prefix_text: Optional[str] = None,
) -> Optional[Message]:
    """
    Send post preview to user's DM.
    
    Args:
        chat_id: User's chat ID
        post: Draft post to preview
        prefix_text: Optional text to prepend (e.g., "Preview:")
        
    Returns:
        Sent message or None if failed
    """
    keyboard = build_keyboard(list(post.buttons))
    
    # Add prefix to text if provided
    text = post.text or ""
    if prefix_text:
        text = f"{prefix_text}\n\n{text}" if text else prefix_text
    
    try:
        # No media - text only
        if not post.media:
            return await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard,
                disable_web_page_preview=post.disable_link_preview,
            )
        
        # Single media
        if len(post.media) == 1:
            media = post.media[0]
            send_methods = {
                "photo": bot.send_photo,
                "video": bot.send_video,
                "document": bot.send_document,
                "audio": bot.send_audio,
                "animation": bot.send_animation,
            }
            
            send_method = send_methods.get(media.media_type, bot.send_photo)
            return await send_method(
                chat_id=chat_id,
                **{media.media_type: media.file_id},
                caption=text,
                reply_markup=keyboard,
            )
        
        # Media group
        media_list = []
        for i, media in enumerate(post.media):
            caption = text if i == 0 else None
            media_list.append(get_input_media(media, caption))
        
        messages = await bot.send_media_group(
            chat_id=chat_id,
            media=media_list,
        )
        
        # Send buttons separately for media groups
        if keyboard and messages:
            await bot.send_message(
                chat_id=chat_id,
                text="👆 <i>Кнопки будут под постом</i>",
                reply_markup=keyboard,
            )
        
        return messages[0] if messages else None
        
    except Exception as e:
        logger.error(f"Failed to send preview to {chat_id}: {e}")
        return None
