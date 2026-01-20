"""Initial tables for draft posts.

Revision ID: 001
Revises: 
Create Date: 2026-01-20

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create draft_posts table
    op.create_table(
        'draft_posts',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('author_id', sa.BigInteger(), nullable=False),
        sa.Column('author_username', sa.String(255), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('text_entities', sa.JSON(), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='draft'),
        sa.Column('published_message_id', sa.BigInteger(), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scheduler_job_id', sa.String(255), nullable=True),
        sa.Column('disable_link_preview', sa.Boolean(), nullable=False, default=True),
        sa.Column('disable_notification', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_draft_posts_author_id', 'draft_posts', ['author_id'])
    op.create_index('ix_draft_posts_scheduled_at', 'draft_posts', ['scheduled_at'])
    op.create_index('ix_draft_posts_status', 'draft_posts', ['status'])
    
    # Create draft_media table
    op.create_table(
        'draft_media',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('post_id', sa.BigInteger(), nullable=False),
        sa.Column('file_id', sa.String(255), nullable=False),
        sa.Column('file_unique_id', sa.String(255), nullable=False),
        sa.Column('media_type', sa.String(20), nullable=False),
        sa.Column('caption', sa.Text(), nullable=True),
        sa.Column('position', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['draft_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create draft_buttons table
    op.create_table(
        'draft_buttons',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('post_id', sa.BigInteger(), nullable=False),
        sa.Column('text', sa.String(255), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('row', sa.Integer(), nullable=False, default=0),
        sa.Column('position', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), onupdate=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['post_id'], ['draft_posts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('draft_buttons')
    op.drop_table('draft_media')
    op.drop_index('ix_draft_posts_status', table_name='draft_posts')
    op.drop_index('ix_draft_posts_scheduled_at', table_name='draft_posts')
    op.drop_index('ix_draft_posts_author_id', table_name='draft_posts')
    op.drop_table('draft_posts')
