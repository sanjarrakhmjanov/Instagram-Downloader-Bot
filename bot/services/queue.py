import json
from dataclasses import asdict, dataclass

from redis.asyncio import Redis

from bot.constants import ACTIVE_JOB_KEY, CANCEL_REQUEST_KEY, PENDING_REQUEST_KEY, QUEUE_KEY


@dataclass
class PendingRequest:
    request_id: str
    user_id: int
    chat_id: int
    url: str
    platform: str
    title: str
    duration_sec: int | None
    language: str


@dataclass
class DownloadJob:
    request_id: str
    user_id: int
    chat_id: int
    url: str
    platform: str
    title: str
    duration_sec: int | None
    option: str
    language: str


class QueueService:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def save_pending(self, item: PendingRequest, ttl_sec: int = 900) -> None:
        key = PENDING_REQUEST_KEY.format(request_id=item.request_id)
        await self.redis.setex(key, ttl_sec, json.dumps(asdict(item)))

    async def get_pending(self, request_id: str) -> PendingRequest | None:
        key = PENDING_REQUEST_KEY.format(request_id=request_id)
        payload = await self.redis.get(key)
        if not payload:
            return None
        data = json.loads(payload)
        return PendingRequest(**data)

    async def delete_pending(self, request_id: str) -> None:
        key = PENDING_REQUEST_KEY.format(request_id=request_id)
        await self.redis.delete(key)

    async def enqueue(self, job: DownloadJob) -> int:
        await self.redis.rpush(QUEUE_KEY, json.dumps(asdict(job)))
        return int(await self.redis.llen(QUEUE_KEY))

    async def dequeue(self, timeout: int = 0) -> DownloadJob | None:
        row = await self.redis.blpop(QUEUE_KEY, timeout=timeout)
        if not row:
            return None
        _, payload = row
        data = json.loads(payload)
        return DownloadJob(**data)

    async def set_active_job(self, user_id: int, request_id: str, ttl_sec: int = 3600) -> None:
        await self.redis.setex(ACTIVE_JOB_KEY.format(user_id=user_id), ttl_sec, request_id)

    async def get_active_job(self, user_id: int) -> str | None:
        return await self.redis.get(ACTIVE_JOB_KEY.format(user_id=user_id))

    async def clear_active_job(self, user_id: int) -> None:
        await self.redis.delete(ACTIVE_JOB_KEY.format(user_id=user_id))

    async def request_cancel(self, request_id: str, ttl_sec: int = 3600) -> None:
        await self.redis.setex(CANCEL_REQUEST_KEY.format(request_id=request_id), ttl_sec, "1")

    async def is_cancel_requested(self, request_id: str) -> bool:
        return bool(await self.redis.exists(CANCEL_REQUEST_KEY.format(request_id=request_id)))

    async def clear_cancel_request(self, request_id: str) -> None:
        await self.redis.delete(CANCEL_REQUEST_KEY.format(request_id=request_id))
