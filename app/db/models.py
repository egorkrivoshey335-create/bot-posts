"""Database models for draft posts."""

from datetime import datetime
from enum import Enum
from typing import List, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, IDMixin, TimestampMixin


class PostStatus(str, Enum):
    """Status of a draft post."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    FAILED = "failed"


class MediaType(str, Enum):
    """Type of media attachment."""

    PHOTO = "photo"
    VIDEO = "video"
    DOCUMENT = "document"
    AUDIO = "audio"
    ANIMATION = "animation"


class DraftPost(Base, IDMixin, TimestampMixin):
    """Draft post model."""

    __tablename__ = "draft_posts"

    # Author info
    author_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    author_username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Post content
    text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Scheduling
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    
    # Status
    status: Mapped[str] = mapped_column(
        String(20), default=PostStatus.DRAFT.value, nullable=False, index=True
    )
    
    # Published message info
    published_message_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    published_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Scheduler job ID
    scheduler_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Disable link preview
    disable_link_preview: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Disable notification
    disable_notification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships
    media: Mapped[List["DraftMedia"]] = relationship(
        "DraftMedia",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    buttons: Mapped[List["DraftButton"]] = relationship(
        "DraftButton",
        back_populates="post",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="DraftButton.row, DraftButton.position",
    )

    def __repr__(self) -> str:
        return f"<DraftPost id={self.id} status={self.status}>"


class DraftMedia(Base, IDMixin, TimestampMixin):
    """Media attachment for draft post."""

    __tablename__ = "draft_media"

    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("draft_posts.id", ondelete="CASCADE"), nullable=False
    )
    
    # Media info
    file_id: Mapped[str] = mapped_column(String(255), nullable=False)
    file_unique_id: Mapped[str] = mapped_column(String(255), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False)
    
    # Optional caption for single media
    caption: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Order in media group
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationship
    post: Mapped["DraftPost"] = relationship("DraftPost", back_populates="media")

    def __repr__(self) -> str:
        return f"<DraftMedia id={self.id} type={self.media_type}>"


class DraftButton(Base, IDMixin, TimestampMixin):
    """Inline button for draft post."""

    __tablename__ = "draft_buttons"

    post_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("draft_posts.id", ondelete="CASCADE"), nullable=False
    )
    
    # Button content
    text: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    
    # Position in keyboard
    row: Mapped[int] = mapped_column(default=0, nullable=False)
    position: Mapped[int] = mapped_column(default=0, nullable=False)

    # Relationship
    post: Mapped["DraftPost"] = relationship("DraftPost", back_populates="buttons")

    def __repr__(self) -> str:
        return f"<DraftButton id={self.id} text={self.text}>"
