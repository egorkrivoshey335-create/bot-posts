"""Tests for draft post repository."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import PostStatus
from app.db.repo import DraftPostRepository


@pytest.mark.asyncio
async def test_create_draft_post(db_session: AsyncSession):
    """Test creating a draft post."""
    repo = DraftPostRepository(db_session)
    
    post = await repo.create(
        author_id=123456789,
        author_username="testuser",
        text="Test post content",
    )
    
    assert post.id is not None
    assert post.author_id == 123456789
    assert post.author_username == "testuser"
    assert post.text == "Test post content"
    assert post.status == PostStatus.DRAFT.value


@pytest.mark.asyncio
async def test_get_by_id(db_session: AsyncSession):
    """Test getting post by ID."""
    repo = DraftPostRepository(db_session)
    
    created = await repo.create(author_id=123, text="Test")
    await db_session.commit()
    
    retrieved = await repo.get_by_id(created.id)
    
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.text == "Test"


@pytest.mark.asyncio
async def test_get_nonexistent_post(db_session: AsyncSession):
    """Test getting non-existent post returns None."""
    repo = DraftPostRepository(db_session)
    
    result = await repo.get_by_id(999999)
    
    assert result is None
