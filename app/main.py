"""Application entrypoint."""

import asyncio
import logging

from app.bot import bot, dp
from app.config import get_settings
from app.db.session import engine
from app.logging_config import setup_logging
from app.middlewares.admin_only import AdminOnlyMiddleware
from app.routers import common, drafts, edit_published, post_wizard
from app.services.scheduler import shutdown_scheduler, start_scheduler

logger = logging.getLogger(__name__)


def register_routers() -> None:
    """Register all routers with the dispatcher."""
    dp.include_router(common.router)
    dp.include_router(post_wizard.router)
    dp.include_router(drafts.router)
    dp.include_router(edit_published.router)


def register_middlewares() -> None:
    """Register middlewares with the dispatcher."""
    settings = get_settings()
    dp.message.middleware(AdminOnlyMiddleware(admin_ids=settings.admin_ids))
    dp.callback_query.middleware(AdminOnlyMiddleware(admin_ids=settings.admin_ids))


async def on_startup() -> None:
    """Startup hook."""
    logger.info("Starting bot...")
    
    # Start scheduler
    await start_scheduler()
    
    # Get bot info
    bot_info = await bot.get_me()
    logger.info(f"Bot started: @{bot_info.username}")


async def on_shutdown() -> None:
    """Shutdown hook."""
    logger.info("Shutting down...")
    
    # Shutdown scheduler
    await shutdown_scheduler()
    
    # Close database connections
    await engine.dispose()
    
    # Close bot session
    await bot.session.close()
    
    logger.info("Bot stopped")


async def main() -> None:
    """Main application entrypoint."""
    # Setup logging
    setup_logging()
    
    # Register handlers
    register_routers()
    register_middlewares()
    
    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Start polling
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        await on_shutdown()


if __name__ == "__main__":
    asyncio.run(main())
