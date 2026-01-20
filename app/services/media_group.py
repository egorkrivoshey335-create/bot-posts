"""Media group collection service."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from aiogram.types import Message

from app.db.models import MediaType

logger = logging.getLogger(__name__)


@dataclass
class MediaItem:
    """Single media item."""
    
    file_id: str
    file_unique_id: str
    media_type: str
    caption: Optional[str] = None


@dataclass
class MediaGroupCollector:
    """Collector for media group (album) messages."""
    
    media_group_id: str
    user_id: int
    messages: List[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_message(self, message: Message) -> None:
        """Add message to group."""
        self.messages.append(message)
    
    def get_media_items(self) -> List[MediaItem]:
        """Extract media items from collected messages."""
        items = []
        
        for msg in sorted(self.messages, key=lambda m: m.message_id):
            media_type = None
            file_id = None
            file_unique_id = None
            caption = msg.caption
            
            if msg.photo:
                # Get highest resolution photo
                photo = msg.photo[-1]
                media_type = MediaType.PHOTO.value
                file_id = photo.file_id
                file_unique_id = photo.file_unique_id
            elif msg.video:
                media_type = MediaType.VIDEO.value
                file_id = msg.video.file_id
                file_unique_id = msg.video.file_unique_id
            elif msg.document:
                media_type = MediaType.DOCUMENT.value
                file_id = msg.document.file_id
                file_unique_id = msg.document.file_unique_id
            elif msg.audio:
                media_type = MediaType.AUDIO.value
                file_id = msg.audio.file_id
                file_unique_id = msg.audio.file_unique_id
            elif msg.animation:
                media_type = MediaType.ANIMATION.value
                file_id = msg.animation.file_id
                file_unique_id = msg.animation.file_unique_id
            
            if file_id and media_type:
                items.append(MediaItem(
                    file_id=file_id,
                    file_unique_id=file_unique_id,
                    media_type=media_type,
                    caption=caption,
                ))
        
        return items


class MediaGroupManager:
    """Manager for collecting media groups."""
    
    def __init__(self, collect_timeout: float = 0.5):
        self._collectors: Dict[str, MediaGroupCollector] = {}
        self._collect_timeout = collect_timeout
        self._locks: Dict[str, asyncio.Lock] = {}
    
    async def process_message(self, message: Message) -> Optional[List[MediaItem]]:
        """
        Process incoming message. Returns collected media items
        if this is the last message in a media group, None otherwise.
        
        For single media (no media_group_id), returns immediately.
        For media groups, waits for all messages to arrive.
        """
        # Single media message
        if not message.media_group_id:
            item = self._extract_single_media(message)
            return [item] if item else None
        
        group_id = message.media_group_id
        
        # Get or create lock for this group
        if group_id not in self._locks:
            self._locks[group_id] = asyncio.Lock()
        
        async with self._locks[group_id]:
            # Get or create collector
            if group_id not in self._collectors:
                self._collectors[group_id] = MediaGroupCollector(
                    media_group_id=group_id,
                    user_id=message.from_user.id if message.from_user else 0,
                )
            
            collector = self._collectors[group_id]
            collector.add_message(message)
        
        # Wait for more messages
        await asyncio.sleep(self._collect_timeout)
        
        # Check if we should process
        async with self._locks[group_id]:
            if group_id not in self._collectors:
                return None
            
            collector = self._collectors.pop(group_id)
            del self._locks[group_id]
            
            return collector.get_media_items()
    
    def _extract_single_media(self, message: Message) -> Optional[MediaItem]:
        """Extract media item from single message."""
        if message.photo:
            photo = message.photo[-1]
            return MediaItem(
                file_id=photo.file_id,
                file_unique_id=photo.file_unique_id,
                media_type=MediaType.PHOTO.value,
                caption=message.caption,
            )
        elif message.video:
            return MediaItem(
                file_id=message.video.file_id,
                file_unique_id=message.video.file_unique_id,
                media_type=MediaType.VIDEO.value,
                caption=message.caption,
            )
        elif message.document:
            return MediaItem(
                file_id=message.document.file_id,
                file_unique_id=message.document.file_unique_id,
                media_type=MediaType.DOCUMENT.value,
                caption=message.caption,
            )
        elif message.audio:
            return MediaItem(
                file_id=message.audio.file_id,
                file_unique_id=message.audio.file_unique_id,
                media_type=MediaType.AUDIO.value,
                caption=message.caption,
            )
        elif message.animation:
            return MediaItem(
                file_id=message.animation.file_id,
                file_unique_id=message.animation.file_unique_id,
                media_type=MediaType.ANIMATION.value,
                caption=message.caption,
            )
        
        return None


# Global manager instance
media_group_manager = MediaGroupManager()
