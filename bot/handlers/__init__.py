from aiogram import Router

from bot.handlers.callbacks import router as callbacks_router
from bot.handlers.commands import router as commands_router
from bot.handlers.link import router as link_router


def setup_routers() -> Router:
    root = Router()
    root.include_router(commands_router)
    root.include_router(callbacks_router)
    root.include_router(link_router)
    return root

