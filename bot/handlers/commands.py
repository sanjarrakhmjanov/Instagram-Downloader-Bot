from html import escape
import logging

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError
from aiogram.types import Message
from aiogram.types import ReplyKeyboardRemove
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import Settings
from bot.db.repo import DownloadRepository, FavoriteRepository, UserRepository
from bot.i18n import tr
from bot.keyboards.common import language_keyboard
from bot.services.queue import QueueService

router = Router()
logger = logging.getLogger(__name__)


async def _lang(message: Message, session: AsyncSession, settings: Settings) -> str:
    if not message.from_user:
        return settings.default_language
    repo = UserRepository(session)
    return await repo.get_language(message.from_user.id, settings.default_language)


async def _send_start_landing(message: Message, settings: Settings, lang: str) -> None:
    text = tr("start", lang)
    remove_kb = ReplyKeyboardRemove()
    if settings.welcome_photo_file_id:
        try:
            await message.answer_photo(
                settings.welcome_photo_file_id,
                caption=text,
                reply_markup=remove_kb,
            )
            return
        except (TelegramBadRequest, TelegramNetworkError) as exc:
            logger.warning("Start photo(file_id) failed: %s", exc)
    if settings.welcome_image_url:
        try:
            await message.answer_photo(
                settings.welcome_image_url,
                caption=text,
                reply_markup=remove_kb,
            )
            return
        except (TelegramBadRequest, TelegramNetworkError) as exc:
            logger.warning("Start photo(url) failed: %s", exc)
    if settings.welcome_animation_url:
        try:
            await message.answer_animation(
                settings.welcome_animation_url,
                caption=text,
                reply_markup=remove_kb,
            )
            return
        except (TelegramBadRequest, TelegramNetworkError) as exc:
            logger.warning("Start animation failed: %s", exc)

    await message.answer(text, reply_markup=remove_kb)


@router.message(Command("start"))
async def cmd_start(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not message.from_user:
        return
    user_repo = UserRepository(session)
    await user_repo.get_or_create(message.from_user.id, settings.default_language)
    lang = await _lang(message, session, settings)
    await _send_start_landing(message, settings, lang)


@router.message(Command("help"))
async def cmd_help(message: Message, session: AsyncSession, settings: Settings) -> None:
    lang = await _lang(message, session, settings)
    await message.answer(tr("help_premium", lang))


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession, settings: Settings) -> None:
    lang = await _lang(message, session, settings)
    await message.answer(tr("settings", lang), reply_markup=language_keyboard("settings"))


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
    lines = [tr("history_header", lang)]
    for idx, row in enumerate(rows, 1):
        lines.append(
            tr(
                "history_item",
                lang,
                idx=idx,
                title=escape(row.title),
                fmt=escape(row.selected_format.upper()),
            )
        )
    await message.answer("\n\n".join(lines))


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
    lines = [tr("favorites_header", lang)]
    for idx, row in enumerate(rows, 1):
        lines.append(
            tr(
                "favorites_item",
                lang,
                idx=idx,
                title=escape(row.title),
                url=escape(row.url),
            )
        )
    await message.answer("\n\n".join(lines))


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
