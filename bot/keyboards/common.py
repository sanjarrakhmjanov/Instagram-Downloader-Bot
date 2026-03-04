from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

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


def start_actions_keyboard(lang: str, is_admin: bool = False) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text=tr("menu_download", lang), callback_data="menu:download"),
            InlineKeyboardButton(text=tr("menu_help", lang), callback_data="menu:help"),
        ],
        [
            InlineKeyboardButton(text=tr("menu_settings", lang), callback_data="menu:settings"),
            InlineKeyboardButton(text=tr("menu_privacy", lang), callback_data="menu:privacy"),
        ],
        [
            InlineKeyboardButton(text=tr("menu_history", lang), callback_data="menu:history"),
            InlineKeyboardButton(text=tr("menu_favorites", lang), callback_data="menu:favorites"),
        ],
    ]
    if is_admin:
        rows.append([InlineKeyboardButton(text=tr("menu_admin", lang), callback_data="menu:admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
