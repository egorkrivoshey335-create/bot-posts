"""Repository pattern for database operations."""

from datetime import datetime
from typing import List, Optional, Sequence

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
    ) -> DraftPost:
        """Create a new draft post."""
        post = DraftPost(
            author_id=author_id,
            author_username=author_username,
            text=text,
            status=PostStatus.DRAFT.value,
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
