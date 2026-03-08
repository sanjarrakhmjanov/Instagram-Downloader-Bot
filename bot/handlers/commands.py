from html import escape

from aiogram import F, Router
from aiogram.dispatcher.event.bases import SkipHandler
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


def _menu_texts() -> dict[str, set[str]]:
    langs = ("uz", "ru", "en")
    return {
        "download": {tr("menu_download", l) for l in langs},
        "help": {tr("menu_help", l) for l in langs},
        "settings": {tr("menu_settings", l) for l in langs},
        "history": {tr("menu_history", l) for l in langs},
        "favorites": {tr("menu_favorites", l) for l in langs},
        "admin": {tr("menu_admin", l) for l in langs},
    }


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


@router.message(F.text)
async def menu_button_handler(message: Message, session: AsyncSession, settings: Settings) -> None:
    if not message.text or not message.from_user:
        return

    labels = _menu_texts()
    text = message.text.strip()
    lang = await _lang(message, session, settings)

    if text in labels["download"]:
        await message.answer(tr("send_link_prompt", lang))
    elif text in labels["help"]:
        await cmd_help(message, session, settings)
    elif text in labels["settings"]:
        await cmd_settings(message, session, settings)
    elif text in labels["history"]:
        await cmd_history(message, session, settings)
    elif text in labels["favorites"]:
        await cmd_favorites(message, session, settings)
    elif text in labels["admin"]:
        await cmd_admin(message, session, settings)
    else:
        raise SkipHandler()


@router.message(F.text.startswith("/"))
async def unknown_command(message: Message) -> None:
    await message.answer("Command not recognized. Use /help")
