"""Drafts and posts management handlers."""

import logging
from datetime import datetime

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.config import get_settings
from app.db.models import PostStatus
from app.db.repo import DraftPostRepository
from app.db.session import get_session
from app.services.datetime_parse import format_datetime

logger = logging.getLogger(__name__)

router = Router(name="drafts")

POSTS_PER_PAGE = 5


def posts_list_keyboard(
    posts: list,
    page: int,
    total_pages: int,
    status_filter: str,
    show_author: bool = False,
) -> InlineKeyboardMarkup:
    """Build keyboard for posts list."""
    kb = []
    
    for post in posts:
        # Status emoji
        status_emoji = {
            PostStatus.DRAFT.value: "📝",
            PostStatus.SCHEDULED.value: "⏰",
            PostStatus.PUBLISHED.value: "✅",
            PostStatus.FAILED.value: "❌",
        }.get(post.status, "❓")
        
        # Text preview
        text_preview = (post.text[:20] + "...") if post.text and len(post.text) > 20 else (post.text or "—")
        
        # Add author for allposts view
        author_str = ""
        if show_author and post.author_username:
            author_str = f"@{post.author_username[:8]} "
        
        kb.append([
            InlineKeyboardButton(
                text=f"{status_emoji} #{post.id} {author_str}{text_preview}",
                callback_data=f"post_view_{post.id}",
            )
        ])
    
    # Pagination
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="◀️", callback_data=f"posts_page_{page-1}_{status_filter}"))
    nav_row.append(InlineKeyboardButton(text=f"{page+1}/{total_pages}", callback_data="posts_noop"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="▶️", callback_data=f"posts_page_{page+1}_{status_filter}"))
    
    if nav_row:
        kb.append(nav_row)
    
    # Filter buttons
    kb.append([
        InlineKeyboardButton(
            text="📝 Черновики" + (" ✓" if status_filter == "draft" else ""),
            callback_data="posts_filter_draft",
        ),
        InlineKeyboardButton(
            text="⏰ Запланированные" + (" ✓" if status_filter == "scheduled" else ""),
            callback_data="posts_filter_scheduled",
        ),
    ])
    kb.append([
        InlineKeyboardButton(
            text="✅ Опубликованные" + (" ✓" if status_filter == "published" else ""),
            callback_data="posts_filter_published",
        ),
        InlineKeyboardButton(
            text="📋 Все" + (" ✓" if status_filter == "all" else ""),
            callback_data="posts_filter_all",
        ),
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


def post_view_keyboard(post) -> InlineKeyboardMarkup:
    """Build keyboard for post view."""
    kb = []
    
    if post.status == PostStatus.DRAFT.value:
        kb.append([
            InlineKeyboardButton(text="📤 Опубликовать", callback_data=f"post_publish_{post.id}"),
            InlineKeyboardButton(text="⏰ Запланировать", callback_data=f"post_schedule_{post.id}"),
        ])
        kb.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"post_edit_{post.id}"),
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"post_delete_{post.id}"),
        ])
    elif post.status == PostStatus.SCHEDULED.value:
        kb.append([
            InlineKeyboardButton(text="📤 Опубликовать сейчас", callback_data=f"post_publish_{post.id}"),
            InlineKeyboardButton(text="❌ Отменить", callback_data=f"post_unschedule_{post.id}"),
        ])
    elif post.status == PostStatus.PUBLISHED.value:
        kb.append([
            InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"post_edit_{post.id}"),
        ])
    
    kb.append([InlineKeyboardButton(text="⬅️ Назад к списку", callback_data="posts_back")])
    
    return InlineKeyboardMarkup(inline_keyboard=kb)


# =============================================================================
# /drafts, /posts commands
# =============================================================================

@router.message(Command("drafts"))
async def cmd_list_drafts(message: Message) -> None:
    """Show list of drafts."""
    await _show_posts_list(message, "draft")


@router.message(Command("posts"))
async def cmd_list_posts(message: Message) -> None:
    """Show list of all posts."""
    await _show_posts_list(message, "all")


@router.message(Command("scheduled"))
async def cmd_list_scheduled(message: Message) -> None:
    """Show list of scheduled posts."""
    await _show_posts_list(message, "scheduled")


@router.message(Command("allposts"))
async def cmd_all_posts(message: Message) -> None:
    """Show all posts from all users (admin only)."""
    settings = get_settings()
    user_id = message.from_user.id
    
    if user_id not in settings.admin_ids:
        await message.answer("❌ Эта команда доступна только администраторам.")
        return
    
    await _show_all_posts_list(message, "all")


async def _show_all_posts_list(message: Message, status_filter: str, page: int = 0) -> None:
    """Show all posts from all users (admin view)."""
    async with get_session() as session:
        repo = DraftPostRepository(session)
        
        status = None
        if status_filter == "draft":
            status = PostStatus.DRAFT
        elif status_filter == "scheduled":
            status = PostStatus.SCHEDULED
        elif status_filter == "published":
            status = PostStatus.PUBLISHED
        
        all_posts = await repo.get_all(status=status, limit=100)
        
        if not all_posts:
            await message.answer(
                "👑 <b>Все посты (админ)</b>\n\n"
                "<i>Постов нет.</i>"
            )
            return
        
        total_pages = (len(all_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        start = page * POSTS_PER_PAGE
        end = start + POSTS_PER_PAGE
        posts_page = all_posts[start:end]
        
        await message.answer(
            f"👑 <b>Все посты (админ)</b> ({len(all_posts)} шт.)\n\n"
            "Выберите пост для просмотра:",
            reply_markup=posts_list_keyboard(posts_page, page, total_pages, f"admin_{status_filter}", show_author=True),
        )
        
        logger.info(f"Admin {message.from_user.id} requested all posts list")


async def _show_posts_list(message: Message, status_filter: str, page: int = 0) -> None:
    """Show posts list with filter."""
    user_id = message.from_user.id
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        
        # Get posts based on filter
        status = None
        if status_filter == "draft":
            status = PostStatus.DRAFT
        elif status_filter == "scheduled":
            status = PostStatus.SCHEDULED
        elif status_filter == "published":
            status = PostStatus.PUBLISHED
        
        all_posts = await repo.get_by_author(user_id, status=status, limit=100)
        
        if not all_posts:
            filter_text = {
                "draft": "черновиков",
                "scheduled": "запланированных постов",
                "published": "опубликованных постов",
                "all": "постов",
            }.get(status_filter, "постов")
            
            await message.answer(
                f"📋 <b>Ваши посты</b>\n\n"
                f"<i>У вас нет {filter_text}.</i>\n\n"
                "Создайте новый пост командой /new"
            )
            return
        
        # Pagination
        total_pages = (len(all_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        start = page * POSTS_PER_PAGE
        end = start + POSTS_PER_PAGE
        posts_page = all_posts[start:end]
        
        filter_title = {
            "draft": "Черновики",
            "scheduled": "Запланированные",
            "published": "Опубликованные",
            "all": "Все посты",
        }.get(status_filter, "Посты")
        
        await message.answer(
            f"📋 <b>{filter_title}</b> ({len(all_posts)} шт.)\n\n"
            "Выберите пост для просмотра:",
            reply_markup=posts_list_keyboard(posts_page, page, total_pages, status_filter),
        )
        
        logger.info(f"User {user_id} requested posts list (filter: {status_filter})")


# =============================================================================
# Pagination and filtering
# =============================================================================

@router.callback_query(F.data.startswith("posts_page_"))
async def handle_page_change(callback: CallbackQuery) -> None:
    """Handle pagination."""
    parts = callback.data.split("_")
    page = int(parts[2])
    status_filter = "_".join(parts[3:])  # Handle admin_all, admin_draft, etc.
    
    user_id = callback.from_user.id
    is_admin_view = status_filter.startswith("admin_")
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        
        # Parse status from filter
        actual_filter = status_filter.replace("admin_", "") if is_admin_view else status_filter
        status = None
        if actual_filter == "draft":
            status = PostStatus.DRAFT
        elif actual_filter == "scheduled":
            status = PostStatus.SCHEDULED
        elif actual_filter == "published":
            status = PostStatus.PUBLISHED
        
        # Get posts based on view type
        if is_admin_view:
            all_posts = await repo.get_all(status=status, limit=100)
        else:
            all_posts = await repo.get_by_author(user_id, status=status, limit=100)
        
        total_pages = (len(all_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        start = page * POSTS_PER_PAGE
        end = start + POSTS_PER_PAGE
        posts_page = all_posts[start:end]
        
        filter_title = {
            "draft": "Черновики",
            "scheduled": "Запланированные",
            "published": "Опубликованные",
            "all": "Все посты",
        }.get(actual_filter, "Посты")
        
        if is_admin_view:
            title = f"👑 <b>Все посты (админ) - {filter_title}</b>"
        else:
            title = f"📋 <b>{filter_title}</b>"
        
        await callback.message.edit_text(
            f"{title} ({len(all_posts)} шт.)\n\n"
            "Выберите пост для просмотра:",
            reply_markup=posts_list_keyboard(posts_page, page, total_pages, status_filter, show_author=is_admin_view),
        )
        await callback.answer()


@router.callback_query(F.data.startswith("posts_filter_"))
async def handle_filter_change(callback: CallbackQuery) -> None:
    """Handle filter change."""
    status_filter = callback.data.split("_")[2]
    
    user_id = callback.from_user.id
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        
        status = None
        if status_filter == "draft":
            status = PostStatus.DRAFT
        elif status_filter == "scheduled":
            status = PostStatus.SCHEDULED
        elif status_filter == "published":
            status = PostStatus.PUBLISHED
        
        all_posts = await repo.get_by_author(user_id, status=status, limit=100)
        
        if not all_posts:
            filter_text = {
                "draft": "черновиков",
                "scheduled": "запланированных постов",
                "published": "опубликованных постов",
                "all": "постов",
            }.get(status_filter, "постов")
            
            await callback.message.edit_text(
                f"📋 <b>Ваши посты</b>\n\n"
                f"<i>У вас нет {filter_text}.</i>\n\n"
                "Создайте новый пост командой /new"
            )
            await callback.answer()
            return
        
        total_pages = (len(all_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        posts_page = all_posts[:POSTS_PER_PAGE]
        
        filter_title = {
            "draft": "Черновики",
            "scheduled": "Запланированные",
            "published": "Опубликованные",
            "all": "Все посты",
        }.get(status_filter, "Посты")
        
        await callback.message.edit_text(
            f"📋 <b>{filter_title}</b> ({len(all_posts)} шт.)\n\n"
            "Выберите пост для просмотра:",
            reply_markup=posts_list_keyboard(posts_page, 0, total_pages, status_filter),
        )
        await callback.answer()


@router.callback_query(F.data == "posts_noop")
async def handle_noop(callback: CallbackQuery) -> None:
    """Handle noop callback (page indicator)."""
    await callback.answer()


@router.callback_query(F.data == "posts_back")
async def handle_back_to_list(callback: CallbackQuery) -> None:
    """Go back to posts list."""
    user_id = callback.from_user.id
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        all_posts = await repo.get_by_author(user_id, limit=100)
        
        if not all_posts:
            await callback.message.edit_text(
                "📋 <b>Ваши посты</b>\n\n"
                "<i>У вас нет постов.</i>\n\n"
                "Создайте новый пост командой /new"
            )
            await callback.answer()
            return
        
        total_pages = (len(all_posts) + POSTS_PER_PAGE - 1) // POSTS_PER_PAGE
        posts_page = all_posts[:POSTS_PER_PAGE]
        
        await callback.message.edit_text(
            f"📋 <b>Все посты</b> ({len(all_posts)} шт.)\n\n"
            "Выберите пост для просмотра:",
            reply_markup=posts_list_keyboard(posts_page, 0, total_pages, "all"),
        )
        await callback.answer()


# =============================================================================
# View post
# =============================================================================

@router.callback_query(F.data.startswith("post_view_"))
async def view_post(callback: CallbackQuery) -> None:
    """View post details."""
    post_id = int(callback.data.split("_")[2])
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return
        
        # Build post info
        status_text = {
            PostStatus.DRAFT.value: "📝 Черновик",
            PostStatus.SCHEDULED.value: "⏰ Запланирован",
            PostStatus.PUBLISHED.value: "✅ Опубликован",
            PostStatus.FAILED.value: "❌ Ошибка публикации",
        }.get(post.status, post.status)
        
        text_preview = post.text[:200] + "..." if post.text and len(post.text) > 200 else (post.text or "<без текста>")
        
        info_parts = [
            f"📋 <b>Пост #{post.id}</b>\n",
            f"<b>Статус:</b> {status_text}",
            f"<b>Создан:</b> {format_datetime(post.created_at)}",
        ]
        
        if post.scheduled_at:
            info_parts.append(f"<b>Запланирован:</b> {format_datetime(post.scheduled_at)}")
        
        if post.published_at:
            info_parts.append(f"<b>Опубликован:</b> {format_datetime(post.published_at)}")
        
        if post.published_message_id:
            info_parts.append(f"<b>ID сообщения:</b> <code>{post.published_message_id}</code>")
        
        info_parts.append(f"\n<b>Медиа:</b> {len(post.media)} файл(ов)")
        info_parts.append(f"<b>Кнопок:</b> {len(post.buttons)}")
        
        if post.buttons:
            buttons_text = "\n".join([f"  • {btn.text}" for btn in post.buttons[:3]])
            if len(post.buttons) > 3:
                buttons_text += f"\n  ... и ещё {len(post.buttons) - 3}"
            info_parts.append(f"\n<b>Кнопки:</b>\n{buttons_text}")
        
        info_parts.append(f"\n<b>Текст:</b>\n<i>{text_preview}</i>")
        
        await callback.message.edit_text(
            "\n".join(info_parts),
            reply_markup=post_view_keyboard(post),
        )
        await callback.answer()


# =============================================================================
# Post actions
# =============================================================================

@router.callback_query(F.data.startswith("post_edit_"))
async def start_edit_post(callback: CallbackQuery) -> None:
    """Redirect to edit post."""
    post_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        f"✏️ Для редактирования поста используйте команду:\n\n"
        f"<code>/edit {post_id}</code>"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("post_delete_"))
async def delete_post(callback: CallbackQuery) -> None:
    """Delete a draft post."""
    post_id = int(callback.data.split("_")[2])
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return
        
        if post.status == PostStatus.PUBLISHED.value:
            await callback.answer("Нельзя удалить опубликованный пост", show_alert=True)
            return
        
        await repo.delete(post_id)
        
        await callback.message.edit_text(
            f"🗑 Пост #{post_id} удалён."
        )
        await callback.answer("Удалено")
        
        logger.info(f"User {callback.from_user.id} deleted post {post_id}")


@router.callback_query(F.data.startswith("post_publish_"))
async def publish_post_now(callback: CallbackQuery) -> None:
    """Publish post immediately."""
    from app.services.publishing import publish_post
    from datetime import timezone
    
    post_id = int(callback.data.split("_")[2])
    
    await callback.answer("⏳ Публикую...")
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await callback.message.edit_text("❌ Пост не найден.")
            return
        
        if post.status == PostStatus.PUBLISHED.value:
            await callback.message.edit_text("⚠️ Пост уже опубликован.")
            return
        
        # Cancel scheduled job if exists
        if post.scheduler_job_id:
            from app.services.scheduler import cancel_scheduled_post
            await cancel_scheduled_post(post.scheduler_job_id)
        
        message_id = await publish_post(post)
        
        if message_id:
            await repo.mark_published(
                post_id=post_id,
                message_id=message_id,
                published_at=datetime.now(timezone.utc),
            )
            
            await callback.message.edit_text(
                f"✅ <b>Пост #{post_id} опубликован!</b>\n\n"
                f"ID сообщения: <code>{message_id}</code>"
            )
            logger.info(f"User {callback.from_user.id} published post {post_id}")
        else:
            await repo.mark_failed(post_id)
            await callback.message.edit_text(
                f"❌ <b>Ошибка публикации поста #{post_id}</b>\n\n"
                "Проверьте, что бот является администратором канала."
            )


@router.callback_query(F.data.startswith("post_unschedule_"))
async def unschedule_post(callback: CallbackQuery) -> None:
    """Cancel scheduled post."""
    post_id = int(callback.data.split("_")[2])
    
    async with get_session() as session:
        repo = DraftPostRepository(session)
        post = await repo.get_by_id(post_id)
        
        if not post:
            await callback.answer("Пост не найден", show_alert=True)
            return
        
        if post.status != PostStatus.SCHEDULED.value:
            await callback.answer("Пост не запланирован", show_alert=True)
            return
        
        # Cancel scheduler job
        if post.scheduler_job_id:
            from app.services.scheduler import cancel_scheduled_post
            await cancel_scheduled_post(post.scheduler_job_id)
        
        # Update status to draft
        await repo.update(
            post_id,
            status=PostStatus.DRAFT.value,
            scheduled_at=None,
            scheduler_job_id=None,
        )
        
        await callback.message.edit_text(
            f"✅ Публикация поста #{post_id} отменена.\n"
            "Пост сохранён как черновик."
        )
        await callback.answer("Отменено")
        
        logger.info(f"User {callback.from_user.id} unscheduled post {post_id}")


@router.callback_query(F.data.startswith("post_schedule_"))
async def schedule_post_prompt(callback: CallbackQuery) -> None:
    """Prompt to schedule post."""
    post_id = int(callback.data.split("_")[2])
    
    await callback.message.edit_text(
        f"⏰ <b>Планирование поста #{post_id}</b>\n\n"
        "Эта функция пока в разработке.\n\n"
        "Используйте /new для создания нового запланированного поста."
    )
    await callback.answer()
