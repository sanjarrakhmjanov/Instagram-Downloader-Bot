import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from redis.asyncio import Redis

from bot.config import get_settings
from bot.db.session import SessionLocal, init_db
from bot.handlers import setup_routers
from bot.json_logger import setup_json_logging
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.services.downloader import DownloaderService

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    setup_json_logging(settings.log_level)

    await init_db()
    redis = Redis.from_url(settings.redis_dsn, decode_responses=True)

    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(setup_routers())

    db_middleware = DbSessionMiddleware(SessionLocal)
    dp.message.middleware(db_middleware)
    dp.callback_query.middleware(db_middleware)

    rate_limit = RateLimitMiddleware(
        redis=redis,
        limit=settings.request_rate_limit,
        window_sec=settings.request_rate_window_sec,
    )
    dp.message.middleware(rate_limit)

    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Welcome"),
            BotCommand(command="help", description="How to use"),
            BotCommand(command="settings", description="Language settings"),
            BotCommand(command="history", description="Download history"),
            BotCommand(command="favorites", description="Saved links"),
            BotCommand(command="cancel", description="Cancel current flow"),
            BotCommand(command="admin", description="Admin stats"),
        ]
    )

    downloader = DownloaderService(
        settings.download_dir,
        settings.request_timeout_sec,
        ffmpeg_location=settings.ffmpeg_path,
    )
    logger.info("Bot started")
    try:
        await dp.start_polling(
            bot,
            redis=redis,
            settings=settings,
            downloader=downloader,
        )
    finally:
        await redis.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
