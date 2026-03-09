from contextlib import suppress

from aiogram import F, Router
from aiogram.exceptions import TelegramNetworkError
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.db.models import Download
from bot.db.repo import FavoriteRepository, UserRepository
from bot.i18n import tr
from bot.services.queue import DownloadJob, QueueService
from bot.states.download import DownloadFlow

router = Router()


@router.callback_query(F.data.startswith("lang:"))
async def cb_set_language(
    callback: CallbackQuery, session: AsyncSession, settings: Settings
) -> None:
    if not callback.from_user or not callback.data:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid language action", show_alert=True)
        return
    _, source, lang = parts
    repo = UserRepository(session)
    await repo.set_language(callback.from_user.id, lang)
    await callback.answer()
    if callback.message:
        try:
            await callback.message.edit_text(tr("language_updated", lang))
        except TelegramNetworkError:
            pass
        if source == "start":
            if settings.welcome_photo_file_id:
                await callback.message.answer_photo(
                    settings.welcome_photo_file_id,
                    caption=tr("start", lang),
                )
            elif settings.welcome_image_url:
                await callback.message.answer_photo(
                    settings.welcome_image_url,
                    caption=tr("start", lang),
                )
            elif settings.welcome_animation_url:
                await callback.message.answer_animation(
                    settings.welcome_animation_url,
                    caption=tr("start", lang),
                )
            else:
                await callback.message.answer(tr("start", lang))


@router.callback_query(F.data.startswith("dl:"))
async def cb_download(
    callback: CallbackQuery,
    redis: Redis,
    session: AsyncSession,
    settings: Settings,
    state: FSMContext,
) -> None:
    if not callback.data or not callback.from_user:
        return
    parts = callback.data.split(":")
    if len(parts) != 3:
        await callback.answer("Invalid action.", show_alert=True)
        return
    _, request_id, option = parts
    queue = QueueService(redis)

    pending = await queue.get_pending(request_id)
    if not pending:
        await callback.answer("Request expired. Send the link again.", show_alert=True)
        await state.clear()
        return

    if option == "cancel":
        await queue.request_cancel(request_id)
        await queue.delete_pending(request_id)
        await state.clear()
        await callback.answer("Canceled", show_alert=False)
        if callback.message:
            await callback.message.edit_text(tr("flow_cancelled", pending.language))
        return

    job = DownloadJob(
        request_id=request_id,
        user_id=pending.user_id,
        chat_id=pending.chat_id,
        url=pending.url,
        platform=pending.platform,
        title=pending.title,
        duration_sec=pending.duration_sec,
        option=option,
        language=pending.language,
    )
    await queue.enqueue(job)
    await queue.delete_pending(request_id)
    await state.clear()
    if callback.message:
        with suppress(Exception):
            await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("fav:add:"))
async def cb_add_favorite(
    callback: CallbackQuery, session: AsyncSession, settings: Settings
) -> None:
    if not callback.from_user or not callback.data:
        return
    download_id = int(callback.data.split(":")[-1])
    row = await session.scalar(select(Download).where(Download.id == download_id))
    repo = UserRepository(session)
    lang = await repo.get_language(callback.from_user.id, settings.default_language)
    if not row:
        await callback.answer(tr("failed", lang), show_alert=True)
        return

    fav_repo = FavoriteRepository(session)
    await fav_repo.add_favorite(
        tg_user_id=callback.from_user.id,
        platform=row.platform,
        url=row.url,
        title=row.title,
    )
    await callback.answer(tr("saved_to_favorites", lang), show_alert=False)
