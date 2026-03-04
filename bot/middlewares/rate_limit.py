from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message
from redis.asyncio import Redis

from bot.constants import RATE_LIMIT_KEY
from bot.i18n import tr


class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, limit: int, window_sec: int):
        self.redis = redis
        self.limit = limit
        self.window_sec = window_sec

    async def __call__(
        self,
        handler: Callable[[Message, dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: dict[str, Any],
    ) -> Any:
        if not event.from_user:
            return await handler(event, data)

        key = RATE_LIMIT_KEY.format(user_id=event.from_user.id)
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, self.window_sec)
        if current > self.limit:
            lang = data.get("language") or "en"
            await event.answer(tr("rate_limited", lang))
            return None
        return await handler(event, data)

