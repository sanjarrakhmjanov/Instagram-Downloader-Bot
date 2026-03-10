import asyncio
import logging
import uuid

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand
from redis.asyncio import Redis

from bot.config import ensure_instagram_cookies_file, get_settings
from bot.db.session import SessionLocal, init_db
from bot.handlers import setup_routers
from bot.json_logger import setup_json_logging
from bot.middlewares.db_session import DbSessionMiddleware
from bot.middlewares.rate_limit import RateLimitMiddleware
from bot.services.downloader import DownloaderService

logger = logging.getLogger(__name__)
POLLING_LOCK_KEY = "bot:polling:lock"
POLLING_LOCK_TTL_SEC = 120


async def main() -> None:
    settings = get_settings()
    setup_json_logging(settings.log_level)
    cookies_file = ensure_instagram_cookies_file(settings)

    await init_db()
    redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    lock_value = uuid.uuid4().hex
    acquired = await redis.set(POLLING_LOCK_KEY, lock_value, ex=POLLING_LOCK_TTL_SEC, nx=True)
    if not acquired:
        logger.error("Another bot polling instance is already active, exiting")
        await redis.aclose()
        return

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
        ]
    )

    downloader = DownloaderService(
        settings.download_dir,
        settings.request_timeout_sec,
        ffmpeg_location=settings.ffmpeg_path,
        instagram_cookies_file=cookies_file,
    )
    logger.info("Bot started")
    lock_running = True

    async def _renew_lock() -> None:
        while lock_running:
            await asyncio.sleep(POLLING_LOCK_TTL_SEC // 3)
            current = await redis.get(POLLING_LOCK_KEY)
            if current != lock_value:
                logger.error("Polling lock lost, stopping bot to avoid conflicts")
                await dp.stop_polling()
                return
            await redis.expire(POLLING_LOCK_KEY, POLLING_LOCK_TTL_SEC)

    renew_task = asyncio.create_task(_renew_lock())
    try:
        await dp.start_polling(
            bot,
            redis=redis,
            settings=settings,
            downloader=downloader,
        )
    finally:
        lock_running = False
        renew_task.cancel()
        if await redis.get(POLLING_LOCK_KEY) == lock_value:
            await redis.delete(POLLING_LOCK_KEY)
        await redis.aclose()
        await bot.session.aclose()


if __name__ == "__main__":
    asyncio.run(main())
