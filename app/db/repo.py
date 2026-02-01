"""Repository pattern for database operations."""

from datetime import datetime
from typing import List, Optional, Sequence, Tuple

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DraftPost, DraftMedia, DraftButton, PostStatus


class DraftPostRepository:
    """Repository for DraftPost operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        author_id: int,
        author_username: Optional[str] = None,
        text: Optional[str] = None,
        text_entities: Optional[List[dict]] = None,
        scheduled_at: Optional[datetime] = None,
        status: PostStatus = PostStatus.DRAFT,
    ) -> DraftPost:
        """Create a new draft post."""
        post = DraftPost(
            author_id=author_id,
            author_username=author_username,
            text=text,
            text_entities=text_entities,
            scheduled_at=scheduled_at,
            status=status.value,
        )
        self.session.add(post)
        await self.session.flush()
        return post

    async def get_by_id(self, post_id: int) -> Optional[DraftPost]:
        """Get draft post by ID."""
        result = await self.session.execute(
            select(DraftPost).where(DraftPost.id == post_id)
        )
        return result.scalar_one_or_none()

    async def get_by_author(
        self,
        author_id: int,
        status: Optional[PostStatus] = None,
        limit: int = 50,
    ) -> Sequence[DraftPost]:
        """Get all draft posts by author."""
        stmt = select(DraftPost).where(DraftPost.author_id == author_id)
        
        if status:
            stmt = stmt.where(DraftPost.status == status.value)
        
        stmt = stmt.order_by(DraftPost.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_scheduled(self) -> Sequence[DraftPost]:
        """Get all scheduled posts."""
        result = await self.session.execute(
            select(DraftPost)
            .where(DraftPost.status == PostStatus.SCHEDULED.value)
            .order_by(DraftPost.scheduled_at.asc())
        )
        return result.scalars().all()

    async def get_all(
        self,
        status: Optional[PostStatus] = None,
        limit: int = 100,
    ) -> Sequence[DraftPost]:
        """Get all posts (for admins)."""
        stmt = select(DraftPost)
        
        if status:
            stmt = stmt.where(DraftPost.status == status.value)
        
        stmt = stmt.order_by(DraftPost.created_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_due_for_publishing(self, now: datetime) -> Sequence[DraftPost]:
        """Get posts that are due for publishing."""
        result = await self.session.execute(
            select(DraftPost)
            .where(
                DraftPost.status == PostStatus.SCHEDULED.value,
                DraftPost.scheduled_at <= now,
            )
            .order_by(DraftPost.scheduled_at.asc())
        )
        return result.scalars().all()

    async def update(
        self,
        post_id: int,
        **kwargs,
    ) -> Optional[DraftPost]:
        """Update draft post."""
        await self.session.execute(
            update(DraftPost)
            .where(DraftPost.id == post_id)
            .values(**kwargs)
        )
        await self.session.flush()
        return await self.get_by_id(post_id)

    async def delete(self, post_id: int) -> bool:
        """Delete draft post."""
        result = await self.session.execute(
            delete(DraftPost).where(DraftPost.id == post_id)
        )
        return result.rowcount > 0

    async def mark_published(
        self,
        post_id: int,
        message_id: int,
        published_at: datetime,
    ) -> Optional[DraftPost]:
        """Mark post as published."""
        return await self.update(
            post_id,
            status=PostStatus.PUBLISHED.value,
            published_message_id=message_id,
            published_at=published_at,
        )

    async def mark_failed(self, post_id: int) -> Optional[DraftPost]:
        """Mark post as failed."""
        return await self.update(post_id, status=PostStatus.FAILED.value)


class DraftMediaRepository:
    """Repository for DraftMedia operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_media(
        self,
        post_id: int,
        file_id: str,
        file_unique_id: str,
        media_type: str,
        caption: Optional[str] = None,
        position: int = 0,
    ) -> DraftMedia:
        """Add media to a draft post."""
        media = DraftMedia(
            post_id=post_id,
            file_id=file_id,
            file_unique_id=file_unique_id,
            media_type=media_type,
            caption=caption,
            position=position,
        )
        self.session.add(media)
        await self.session.flush()
        return media

    async def get_by_post(self, post_id: int) -> Sequence[DraftMedia]:
        """Get all media for a post."""
        result = await self.session.execute(
            select(DraftMedia)
            .where(DraftMedia.post_id == post_id)
            .order_by(DraftMedia.position)
        )
        return result.scalars().all()

    async def delete_by_post(self, post_id: int) -> int:
        """Delete all media for a post."""
        result = await self.session.execute(
            delete(DraftMedia).where(DraftMedia.post_id == post_id)
        )
        return result.rowcount


class DraftButtonRepository:
    """Repository for DraftButton operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_button(
        self,
        post_id: int,
        text: str,
        url: str,
        row: int = 0,
        position: int = 0,
    ) -> DraftButton:
        """Add button to a draft post."""
        button = DraftButton(
            post_id=post_id,
            text=text,
            url=url,
            row=row,
            position=position,
        )
        self.session.add(button)
        await self.session.flush()
        return button

    async def get_by_post(self, post_id: int) -> Sequence[DraftButton]:
        """Get all buttons for a post."""
        result = await self.session.execute(
            select(DraftButton)
            .where(DraftButton.post_id == post_id)
            .order_by(DraftButton.row, DraftButton.position)
        )
        return result.scalars().all()

    async def delete_by_post(self, post_id: int) -> int:
        """Delete all buttons for a post."""
        result = await self.session.execute(
            delete(DraftButton).where(DraftButton.post_id == post_id)
        )
        return result.rowcount

    async def update_button(
        self,
        button_id: int,
        **kwargs,
    ) -> Optional[DraftButton]:
        """Update a button."""
        await self.session.execute(
            update(DraftButton)
            .where(DraftButton.id == button_id)
            .values(**kwargs)
        )
        await self.session.flush()
        result = await self.session.execute(
            select(DraftButton).where(DraftButton.id == button_id)
        )
        return result.scalar_one_or_none()

    async def delete_button(self, button_id: int) -> bool:
        """Delete a button."""
        result = await self.session.execute(
            delete(DraftButton).where(DraftButton.id == button_id)
        )
        return result.rowcount > 0


async def create_post_with_relations(
    session: "AsyncSession",
    author_id: int,
    author_username: Optional[str] = None,
    text: Optional[str] = None,
    text_entities: Optional[List[dict]] = None,
    media_items: Optional[List[dict]] = None,
    buttons: Optional[List[Tuple[str, str]]] = None,
    scheduled_at: Optional[datetime] = None,
    status: PostStatus = PostStatus.DRAFT,
) -> DraftPost:
    """
    Create a post with all related media and buttons in one transaction.
    
    Args:
        session: Database session
        author_id: Telegram user ID
        author_username: Telegram username
        text: Post text/caption
        text_entities: Serialized MessageEntity objects
        media_items: List of dicts with file_id, file_unique_id, media_type
        buttons: List of (text, url) tuples
        scheduled_at: Optional scheduled publication time
        status: Post status
        
    Returns:
        Created DraftPost with relations
    """
    # Create post
    post_repo = DraftPostRepository(session)
    post = await post_repo.create(
        author_id=author_id,
        author_username=author_username,
        text=text,
        text_entities=text_entities,
        scheduled_at=scheduled_at,
        status=status,
    )
    
    # Add media
    if media_items:
        media_repo = DraftMediaRepository(session)
        for i, media in enumerate(media_items):
            await media_repo.add_media(
                post_id=post.id,
                file_id=media["file_id"],
                file_unique_id=media.get("file_unique_id", media["file_id"]),
                media_type=media["media_type"],
                position=i,
            )
    
    # Add buttons
    if buttons:
        button_repo = DraftButtonRepository(session)
        for i, (btn_text, btn_url) in enumerate(buttons):
            await button_repo.add_button(
                post_id=post.id,
                text=btn_text,
                url=btn_url,
                row=i,
                position=0,
            )
    
    # Refresh to get relations
    await session.refresh(post)
    return post
