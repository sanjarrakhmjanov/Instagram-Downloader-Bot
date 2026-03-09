import re
import uuid
from html import escape
from urllib.parse import urlparse

from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.db.repo import UserRepository
from bot.i18n import tr
from bot.keyboards.common import format_keyboard
from bot.services.downloader import DownloaderService
from bot.services.platforms import detect_platform, normalize_url
from bot.services.queue import DownloadJob, PendingRequest, QueueService
from bot.states.download import DownloadFlow

router = Router()
URL_RE = re.compile(r"(https?://[^\s]+)")


def _extract_url(text: str) -> str | None:
    match = URL_RE.search(text.strip())
    return match.group(1) if match else None


def _format_duration(value: int | float | None) -> str:
    if isinstance(value, (int, float)):
        total_sec = max(0, int(value))
        return f"{total_sec // 60:02d}:{total_sec % 60:02d}"
    return "N/A"


@router.message(F.text)
async def handle_link(
    message: Message,
    session: AsyncSession,
    settings: Settings,
    redis: Redis,
    downloader: DownloaderService,
    state: FSMContext,
) -> None:
    if not message.from_user or not message.text:
        return

    url = _extract_url(message.text)
    if not url:
        return
    url = normalize_url(url)

    user_repo = UserRepository(session)
    lang = await user_repo.get_language(message.from_user.id, settings.default_language)

    platform = detect_platform(url)
    if not platform:
        await message.answer(tr("unsupported_platform", lang))
        return

    progress_msg = await message.answer(tr("fetching_metadata", lang))
    try:
        metadata = await downloader.fetch_metadata(url)
    except Exception:
        try:
            await progress_msg.edit_text(tr("failed", lang))
        except TelegramNetworkError:
            await message.answer(tr("failed", lang))
        return

    request_id = uuid.uuid4().hex[:12]
    queue = QueueService(redis)
    await queue.save_pending(
        PendingRequest(
            request_id=request_id,
            user_id=message.from_user.id,
            chat_id=message.chat.id,
            url=metadata.webpage_url,
            platform=platform,
            title=metadata.title,
            duration_sec=metadata.duration_sec,
            language=lang,
        ),
        ttl_sec=settings.request_timeout_sec,
    )

    # Use the original normalized URL for routing decisions.
    # Metadata URL may be altered/fallback and can lose post/reel semantics.
    path = urlparse(url).path.lower().lstrip("/")
    is_instagram_post = path.startswith("p/")
    is_instagram_reel = path.startswith("reel/")
    is_instagram_video_post = path.startswith("tv/")

    # Reels/video-posts -> format buttons; classic posts/carousels -> auto.
    # Unknown/other Instagram paths default to auto to avoid wrong format UI on image posts.
    if platform == "instagram" and not (is_instagram_reel or is_instagram_video_post):
        await queue.enqueue(
            DownloadJob(
                request_id=request_id,
                user_id=message.from_user.id,
                chat_id=message.chat.id,
                url=metadata.webpage_url,
                platform=platform,
                title=metadata.title,
                duration_sec=metadata.duration_sec,
                option="video",
                language=lang,
            )
        )
        await queue.delete_pending(request_id)
        await state.clear()
        auto_text = tr("auto_processing", lang)
        try:
            await progress_msg.edit_text(auto_text)
        except TelegramNetworkError:
            await message.answer(auto_text)
        return

    await state.set_state(DownloadFlow.awaiting_format)
    await state.update_data(request_id=request_id)

    caption = tr(
        "meta_card",
        lang,
        platform=escape(platform),
        title=escape(metadata.title),
        duration=_format_duration(metadata.duration_sec),
    )
    try:
        await progress_msg.edit_text(caption, reply_markup=format_keyboard(request_id, lang))
    except TelegramNetworkError:
        await message.answer(caption, reply_markup=format_keyboard(request_id, lang))


@router.message(StateFilter(DownloadFlow.awaiting_format), F.text)
async def waiting_format_hint(
    message: Message,
    session: AsyncSession,
    settings: Settings,
) -> None:
    if not message.from_user:
        return
    lang = await UserRepository(session).get_language(message.from_user.id, settings.default_language)
    await message.answer(tr("flow_waiting_format", lang))
