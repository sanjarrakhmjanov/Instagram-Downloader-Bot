from html import escape

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.db.repo import DownloadRepository, FavoriteRepository, UserRepository
from bot.i18n import tr
from bot.keyboards.common import language_keyboard, start_actions_keyboard
from bot.services.queue import QueueService

router = Router()


async def _lang(message: Message, session: AsyncSession, settings: Settings) -> str:
    if not message.from_user:
        return settings.default_language
    repo = UserRepository(session)
    return await repo.get_language(message.from_user.id, settings.default_language)


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not message.from_user:
        return
    user_repo = UserRepository(session)
    await user_repo.get_or_create(message.from_user.id, settings.default_language)
    await message.answer(
        tr("start_choose_language", settings.default_language),
        reply_markup=language_keyboard("start"),
    )


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, settings: Settings) -> None:
    lang = await _lang(message, session, settings)
    await message.answer(tr("help", lang))


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession, settings: Settings) -> None:
    lang = await _lang(message, session, settings)
    await message.answer(tr("settings", lang), reply_markup=language_keyboard("settings"))


@router.message(Command("privacy"))
async def cmd_privacy(message: Message, session: AsyncSession, settings: Settings) -> None:
    lang = await _lang(message, session, settings)
    await message.answer(tr("privacy", lang))


@router.message(Command("cancel"))
async def cmd_cancel(
    message: Message,
    session: AsyncSession,
    settings: Settings,
    state: FSMContext,
    redis: Redis,
) -> None:
    lang = await _lang(message, session, settings)
    queue = QueueService(redis)
    data = await state.get_data()
    request_id = data.get("request_id")
    if isinstance(request_id, str) and request_id:
        await queue.request_cancel(request_id)
        await queue.delete_pending(request_id)

    if message.from_user:
        active_request_id = await queue.get_active_job(message.from_user.id)
        if active_request_id:
            await queue.request_cancel(active_request_id)

    await state.clear()
    await message.answer(tr("flow_cancelled", lang))


@router.message(Command("history"))
async def cmd_history(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not message.from_user:
        return
    lang = await _lang(message, session, settings)
    repo = DownloadRepository(session)
    rows = await repo.list_recent(message.from_user.id)
    if not rows:
        await message.answer(tr("history_empty", lang))
        return
    text = "\n".join(
        f"{idx}. [{escape(row.platform)}] {escape(row.title)} ({escape(row.selected_format)})"
        for idx, row in enumerate(rows, 1)
    )
    await message.answer(text)


@router.message(Command("favorites"))
async def cmd_favorites(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not message.from_user:
        return
    lang = await _lang(message, session, settings)
    repo = FavoriteRepository(session)
    rows = await repo.list_recent(message.from_user.id)
    if not rows:
        await message.answer(tr("favorites_empty", lang))
        return
    text = "\n".join(
        f"{idx}. [{escape(row.platform)}] {escape(row.title)}\n{escape(row.url)}"
        for idx, row in enumerate(rows, 1)
    )
    await message.answer(text)


@router.message(Command("admin"))
async def cmd_admin(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not message.from_user:
        return
    lang = await _lang(message, session, settings)
    if message.from_user.id not in settings.admin_ids:
        await message.answer(tr("admin_only", lang))
        return

    user_repo = UserRepository(session)
    stats = await user_repo.get_stats()
    await message.answer(
        tr(
            "admin_stats_card",
            lang,
            users=stats["users"],
            downloads=stats["downloads"],
            favorites=stats["favorites"],
        )
    )


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message) -> None:
    await message.answer("Command not recognized. Use /help")
