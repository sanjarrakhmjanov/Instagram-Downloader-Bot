import asyncio

from redis.asyncio import Redis
from sqlalchemy import text

from bot.config import get_settings
from bot.db.session import engine


async def main() -> None:
    settings = get_settings()
    redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    pong = await redis.ping()
    await redis.close()

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))

    if not pong:
        raise RuntimeError("Redis ping failed")


if __name__ == "__main__":
    asyncio.run(main())

