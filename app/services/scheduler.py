"""APScheduler integration for scheduled posts."""

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger

from app.config import get_settings

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: Optional[AsyncIOScheduler] = None


async def start_scheduler() -> None:
    """Initialize and start the APScheduler."""
    global scheduler
    
    settings = get_settings()
    
    scheduler = AsyncIOScheduler(
        timezone=settings.tz,
        job_defaults={
            "coalesce": True,
            "max_instances": 1,
            "misfire_grace_time": 60 * 5,  # 5 minutes
        },
    )
    
    # Restore scheduled jobs from database
    await restore_scheduled_jobs()
    
    scheduler.start()
    logger.info(f"Scheduler started with timezone: {settings.tz}")


async def shutdown_scheduler() -> None:
    """Shutdown the scheduler gracefully."""
    global scheduler
    
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped")


async def restore_scheduled_jobs() -> None:
    """Restore scheduled jobs from database after restart."""
    logger.info("Restoring scheduled jobs from database...")
    
    try:
        from app.db.session import get_session
        from app.db.repo import DraftPostRepository
        from app.services.publishing import publish_scheduled_post
        
        async with get_session() as session:
            repo = DraftPostRepository(session)
            scheduled_posts = await repo.get_scheduled()
            
            count = 0
            for post in scheduled_posts:
                if post.scheduled_at and scheduler:
                    job_id = f"publish_post_{post.id}"
                    scheduler.add_job(
                        publish_scheduled_post,
                        trigger=DateTrigger(run_date=post.scheduled_at),
                        id=job_id,
                        args=[post.id],
                        replace_existing=True,
                    )
                    count += 1
                    logger.debug(f"Restored job for post {post.id} at {post.scheduled_at}")
            
            logger.info(f"Restored {count} scheduled jobs from database")
    except Exception as e:
        logger.error(f"Failed to restore scheduled jobs: {e}")


async def schedule_post(
    post_id: int,
    scheduled_at: datetime,
) -> str:
    """
    Schedule a post for publication.
    
    Args:
        post_id: ID of the draft post
        scheduled_at: When to publish the post
        
    Returns:
        Job ID for the scheduled task
    """
    global scheduler
    
    if not scheduler:
        raise RuntimeError("Scheduler is not initialized")
    
    job_id = f"publish_post_{post_id}"
    
    # Import here to avoid circular imports
    from app.services.publishing import publish_scheduled_post
    
    scheduler.add_job(
        publish_scheduled_post,
        trigger=DateTrigger(run_date=scheduled_at),
        id=job_id,
        args=[post_id],
        replace_existing=True,
    )
    
    logger.info(f"Scheduled post {post_id} for {scheduled_at}")
    return job_id


async def cancel_scheduled_post(job_id: str) -> bool:
    """
    Cancel a scheduled post.
    
    Args:
        job_id: Job ID to cancel
        
    Returns:
        True if job was cancelled, False if not found
    """
    global scheduler
    
    if not scheduler:
        return False
    
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Cancelled scheduled job: {job_id}")
        return True
    except Exception as e:
        logger.warning(f"Failed to cancel job {job_id}: {e}")
        return False


def get_scheduler() -> Optional[AsyncIOScheduler]:
    """Get the scheduler instance."""
    return scheduler
