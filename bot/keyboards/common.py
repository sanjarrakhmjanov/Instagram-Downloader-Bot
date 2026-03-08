from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.constants import DOWNLOAD_OPTIONS, SUPPORTED_LANGUAGES
from bot.i18n import tr


def language_keyboard(source: str = "settings") -> InlineKeyboardMarkup:
    labels = {
        "uz": "🇺🇿 O'zbekcha",
        "ru": "🇷🇺 Русский",
        "en": "🇬🇧 English",
    }
    rows = [
        [
            InlineKeyboardButton(text=labels["uz"], callback_data=f"lang:{source}:uz"),
            InlineKeyboardButton(text=labels["ru"], callback_data=f"lang:{source}:ru"),
        ],
        [InlineKeyboardButton(text=labels["en"], callback_data=f"lang:{source}:en")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_keyboard(request_id: str, lang: str = "en") -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=DOWNLOAD_OPTIONS["video"]["label"], callback_data=f"dl:{request_id}:video"),
        ],
        [
            InlineKeyboardButton(text=DOWNLOAD_OPTIONS["mp3"]["label"], callback_data=f"dl:{request_id}:mp3"),
            InlineKeyboardButton(text=tr("btn_cancel", lang), callback_data=f"dl:{request_id}:cancel"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def favorite_keyboard(download_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⭐ Favorite", callback_data=f"fav:add:{download_id}")]
        ]
    )


def favorite_keyboard_localized(download_id: int, lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=tr("favorite_button", lang), callback_data=f"fav:add:{download_id}")]
        ]
    )


def start_actions_keyboard(lang: str, is_admin: bool = False) -> ReplyKeyboardMarkup:
    rows = [
        [
            KeyboardButton(text=tr("menu_download", lang)),
        ],
        [
            KeyboardButton(text=tr("menu_help", lang)),
            KeyboardButton(text=tr("menu_history", lang)),
        ],
        [
            KeyboardButton(text=tr("menu_favorites", lang)),
            KeyboardButton(text=tr("menu_settings", lang)),
        ],
    ]
    if is_admin:
        rows.append([KeyboardButton(text=tr("menu_admin", lang))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
