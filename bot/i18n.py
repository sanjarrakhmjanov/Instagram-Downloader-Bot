from bot.constants import SUPPORTED_LANGUAGES

TEXTS = {
    "start": {
        "uz": (
            "🚀 <b>@saveviathisbot</b> orqali Instagram media yuklab oling.\n\n"
            "<b>Instagram Downloader botiga xush kelibsiz.</b>\n\n"
            "<b>Qo'llab-quvvatlanadi:</b>\n"
            "• Instagram Reels\n"
            "• Instagram Posts (video/rasm)\n"
            "• MP3 audio extract\n\n"
            "<b>Ishlash tartibi:</b>\n"
            "1) Instagram havola yuboring\n"
            "2) <b>VIDEO</b> yoki <b>MP3</b> ni tanlang\n"
            "3) Tayyor faylni qabul qiling"
        ),
        "ru": (
            "🚀 Скачивайте Instagram медиа через <b>@saveviathisbot</b>.\n\n"
            "<b>Добро пожаловать в Instagram Downloader.</b>\n\n"
            "<b>Поддерживается:</b>\n"
            "• Instagram Reels\n"
            "• Instagram Posts (видео/фото)\n"
            "• MP3 извлечение аудио\n\n"
            "<b>Как это работает:</b>\n"
            "1) Отправьте ссылку Instagram\n"
            "2) Выберите <b>VIDEO</b> или <b>MP3</b>\n"
            "3) Получите готовый файл"
        ),
        "en": (
            "🚀 Download Instagram media via <b>@saveviathisbot</b>.\n\n"
            "<b>Welcome to Instagram Downloader.</b>\n\n"
            "<b>Supported:</b>\n"
            "• Instagram Reels\n"
            "• Instagram Posts (video/photo)\n"
            "• MP3 audio extraction\n\n"
            "<b>How it works:</b>\n"
            "1) Send an Instagram link\n"
            "2) Choose <b>VIDEO</b> or <b>MP3</b>\n"
            "3) Receive the ready file"
        ),
    },
    "promo_line": {
        "uz": "🚀 @saveviathisbot orqali Instagram video va MP3 ni tez yuklab oling!",
        "ru": "🚀 Быстро скачивайте Instagram видео и MP3 через @saveviathisbot!",
        "en": "🚀 Download Instagram videos and MP3 quickly via @saveviathisbot!",
    },
    "help": {
        "uz": "Instagram havola yuboring. Video yoki MP3 tanlang.",
        "ru": "Отправьте ссылку Instagram. Выберите Video или MP3.",
        "en": "Send an Instagram link. Choose Video or MP3.",
    },
    "help_premium": {
        "uz": (
            "📘 Premium qo'llanma\n\n"
            "1) Instagram link yuboring\n"
            "2) Kerakli formatni tanlang:\n"
            "• VIDEO — mobilga mos formatda\n"
            "• MP3 — toza audio\n"
            "3) Tayyor faylni qabul qiling\n\n"
            "💡 Eslatma:\n"
            "• Carousel postlarda barcha rasmlar yuboriladi\n"
            "• /cancel bilan jarayonni to'xtatish mumkin"
        ),
        "ru": (
            "📘 Premium инструкция\n\n"
            "1) Отправьте ссылку Instagram\n"
            "2) Выберите формат:\n"
            "• VIDEO — мобильный совместимый формат\n"
            "• MP3 — чистое аудио\n"
            "3) Получите готовый файл\n\n"
            "💡 Примечание:\n"
            "• Для карусели отправляются все фото\n"
            "• /cancel останавливает процесс"
        ),
        "en": (
            "📘 Premium guide\n\n"
            "1) Send an Instagram link\n"
            "2) Choose format:\n"
            "• VIDEO — mobile-compatible output\n"
            "• MP3 — clean audio extraction\n"
            "3) Receive the ready file\n\n"
            "💡 Notes:\n"
            "• Carousel posts send all photos\n"
            "• /cancel stops the current process"
        ),
    },
    "unsupported_platform": {
        "uz": "Faqat Instagram linklari qo'llab-quvvatlanadi.",
        "ru": "Поддерживаются только ссылки Instagram.",
        "en": "Only Instagram links are supported.",
    },
    "invalid_link": {
        "uz": "Noto'g'ri havola yuborildi.",
        "ru": "Отправлена некорректная ссылка.",
        "en": "The provided link is invalid.",
    },
    "fetching_metadata": {
        "uz": "Ma'lumot olinmoqda...",
        "ru": "Получаю метаданные...",
        "en": "Fetching metadata...",
    },
    "choose_format": {
        "uz": "Formatni tanlang:",
        "ru": "Выберите формат:",
        "en": "Choose format:",
    },
    "meta_card": {
        "uz": (
            "📥 Yuklab olish ma'lumoti\n"
            "🌐 Platforma: {platform}\n"
            "🎬 Nomi: {title}\n"
            "⏱ Davomiyligi: {duration}\n\n"
            "Kerakli formatni tanlang."
        ),
        "ru": (
            "📥 Данные загрузки\n"
            "🌐 Платформа: {platform}\n"
            "🎬 Название: {title}\n"
            "⏱ Длительность: {duration}\n\n"
            "Выберите нужный формат."
        ),
        "en": (
            "📥 Download preview\n"
            "🌐 Platform: {platform}\n"
            "🎬 Title: {title}\n"
            "⏱ Duration: {duration}\n\n"
            "Select your output format."
        ),
    },
    "queued": {
        "uz": "⏳ So'rov qabul qilindi.",
        "ru": "⏳ Запрос принят.",
        "en": "⏳ Request accepted.",
    },
    "auto_processing": {
        "uz": "🖼 Instagram post aniqlandi. Format tanlashsiz avtomatik yuklab olinadi.",
        "ru": "🖼 Обнаружен Instagram post. Загрузка запущена автоматически без выбора формата.",
        "en": "🖼 Instagram post detected. Processing automatically without format selection.",
    },
    "processing": {
        "uz": "🕒 Yuklanmoqda:\n{progress}",
        "ru": "🕒 Загрузка:\n{progress}",
        "en": "🕒 Downloading:\n{progress}",
    },
    "done": {
        "uz": "✅ Tayyor. Media muvaffaqiyatli yuborildi.",
        "ru": "✅ Готово. Медиа успешно отправлено.",
        "en": "✅ Done. Media delivered successfully.",
    },
    "completed_card": {
        "uz": "✅ Yuklab olindi\n🎬 Nomi: {title}\n🎵 Format: {fmt}",
        "ru": "✅ Загрузка завершена\n🎬 Название: {title}\n🎵 Формат: {fmt}",
        "en": "✅ Download complete\n🎬 Title: {title}\n🎵 Format: {fmt}",
    },
    "failed": {
        "uz": "Kechirasiz, yuklab olishda xatolik yuz berdi.",
        "ru": "Ошибка во время загрузки.",
        "en": "Download failed.",
    },
    "instagram_restricted": {
        "uz": "Instagram ushbu postni ochishga ruxsat bermadi (private yoki cheklangan).",
        "ru": "Instagram не разрешил доступ к этому посту (private или ограничен).",
        "en": "Instagram denied access to this post (private or restricted).",
    },
    "source_unavailable": {
        "uz": "Manba kontenti topilmadi yoki vaqtincha mavjud emas.",
        "ru": "Источник не найден или временно недоступен.",
        "en": "Source content was not found or is temporarily unavailable.",
    },
    "flow_cancelled": {
        "uz": "Jarayon bekor qilindi.",
        "ru": "Процесс отменен.",
        "en": "Flow canceled.",
    },
    "flow_back": {
        "uz": "Format tanlash oynasiga qaytdingiz.",
        "ru": "Вы вернулись к выбору формата.",
        "en": "Returned to format selection.",
    },
    "flow_waiting_format": {
        "uz": "Iltimos, formatni tugmalar orqali tanlang yoki Cancel bosing.",
        "ru": "Выберите формат кнопками или нажмите Cancel.",
        "en": "Please choose a format using buttons or tap Cancel.",
    },
    "btn_back": {
        "uz": "⬅️ Orqaga",
        "ru": "⬅️ Назад",
        "en": "⬅️ Back",
    },
    "btn_cancel": {
        "uz": "✖️ Bekor qilish",
        "ru": "✖️ Отмена",
        "en": "✖️ Cancel",
    },
    "rate_limited": {
        "uz": "Juda ko'p so'rov yubordingiz. Biroz kutib qayta urinib ko'ring.",
        "ru": "Слишком много запросов. Попробуйте чуть позже.",
        "en": "Too many requests. Please try again shortly.",
    },
    "settings": {
        "uz": "Tilni tanlang:",
        "ru": "Выберите язык:",
        "en": "Choose language:",
    },
    "start_choose_language": {
        "uz": (
            "🔥 Assalomu alaykum, @saveviathisbot ga xush kelibsiz!\n\n"
            "Bu bot Instagram havolalaridan media yuklab beradi:\n"
            "• Reels va video postlar\n"
            "• Carousel postlar (bir nechta rasm)\n"
            "• MP3 (audio extract)\n\n"
            "Qanday ishlaydi:\n"
            "1) Instagram havola yuboring\n"
            "2) Video yoki MP3 tanlang\n"
            "3) Bot tayyor faylni yuboradi\n\n"
            "Davom etish uchun interfeys tilini tanlang."
        ),
        "ru": (
            "🔥 Добро пожаловать в @saveviathisbot!\n\n"
            "Бот загружает медиа по ссылкам Instagram:\n"
            "• Reels и видео-посты\n"
            "• Карусель-посты (несколько фото)\n"
            "• MP3 (извлечение аудио)\n\n"
            "Как это работает:\n"
            "1) Отправьте ссылку Instagram\n"
            "2) Выберите Video или MP3\n"
            "3) Получите готовый файл\n\n"
            "Для продолжения выберите язык интерфейса."
        ),
        "en": (
            "🔥 Welcome to @saveviathisbot!\n\n"
            "This bot downloads media from Instagram links:\n"
            "• Reels and video posts\n"
            "• Carousel posts (multiple photos)\n"
            "• MP3 (audio extraction)\n\n"
            "How it works:\n"
            "1) Send an Instagram link\n"
            "2) Choose Video or MP3\n"
            "3) Receive the ready file\n\n"
            "To continue, choose your interface language."
        ),
    },
    "start_language_hint": {
        "uz": "Avval tilni tanlang:",
        "ru": "Сначала выберите язык:",
        "en": "Choose your language first:",
    },
    "start_quick_actions": {
        "uz": "🧭 Asosiy menyu:",
        "ru": "🧭 Главное меню:",
        "en": "🧭 Main menu:",
    },
    "menu_download": {
        "uz": "⬇️ Yuklab olish",
        "ru": "⬇️ Скачать",
        "en": "⬇️ Download",
    },
    "menu_help": {
        "uz": "📘 Qo'llanma",
        "ru": "📘 Инструкция",
        "en": "📘 Guide",
    },
    "menu_settings": {
        "uz": "🌐 Til",
        "ru": "🌐 Язык",
        "en": "🌐 Language",
    },
    "menu_history": {
        "uz": "🕓 Tarix",
        "ru": "🕓 История",
        "en": "🕓 History",
    },
    "menu_favorites": {
        "uz": "⭐ Sevimlilar",
        "ru": "⭐ Избранное",
        "en": "⭐ Favorites",
    },
    "menu_admin": {
        "uz": "🛠 Admin",
        "ru": "🛠 Админ",
        "en": "🛠 Admin",
    },
    "send_link_prompt": {
        "uz": "Instagram havolasini yuboring.",
        "ru": "Отправьте ссылку Instagram.",
        "en": "Send an Instagram link.",
    },
    "language_updated": {
        "uz": "Til yangilandi.",
        "ru": "Язык обновлен.",
        "en": "Language updated.",
    },
    "history_header": {
        "uz": "🕓 Premium tarix",
        "ru": "🕓 Premium история",
        "en": "🕓 Premium history",
    },
    "history_item": {
        "uz": "#{idx} • {title}\n🎵 Format: {fmt}",
        "ru": "#{idx} • {title}\n🎵 Формат: {fmt}",
        "en": "#{idx} • {title}\n🎵 Format: {fmt}",
    },
    "history_empty": {
        "uz": "Tarix bo'sh.",
        "ru": "История пуста.",
        "en": "History is empty.",
    },
    "favorites_empty": {
        "uz": "⭐ <b>Premium Sevimlilar</b>\n\nHozircha saqlangan media yo'q.\nInstagram link yuboring va natijadan keyin <b>Premium Sevimli</b> tugmasini bosing.",
        "ru": "⭐ <b>Premium Избранное</b>\n\nПока нет сохранённых медиа.\nОтправьте Instagram ссылку и после результата нажмите <b>Premium Избранное</b>.",
        "en": "⭐ <b>Premium Favorites</b>\n\nNo saved media yet.\nSend an Instagram link and tap <b>Premium Favorite</b> after delivery.",
    },
    "saved_to_favorites": {
        "uz": "Sevimlilarga saqlandi.",
        "ru": "Сохранено в избранное.",
        "en": "Saved to favorites.",
    },
    "favorite_button": {
        "uz": "⭐ Premium Sevimli",
        "ru": "⭐ Premium Избранное",
        "en": "⭐ Premium Favorite",
    },
    "favorites_header": {
        "uz": "⭐ <b>Premium Sevimlilar</b>\nSaqlangan media ro'yxati:",
        "ru": "⭐ <b>Premium Избранное</b>\nСписок сохранённых медиа:",
        "en": "⭐ <b>Premium Favorites</b>\nSaved media list:",
    },
    "favorites_item": {
        "uz": "┏ #{idx}\n┃ 🎬 <b>{title}</b>\n┃ 🔗 {url}\n┗━━━━━━━━━━━━",
        "ru": "┏ #{idx}\n┃ 🎬 <b>{title}</b>\n┃ 🔗 {url}\n┗━━━━━━━━━━━━",
        "en": "┏ #{idx}\n┃ 🎬 <b>{title}</b>\n┃ 🔗 {url}\n┗━━━━━━━━━━━━",
    },
    "admin_only": {
        "uz": "⛔ Bu bo'lim faqat administratorlar uchun ochiq.",
        "ru": "⛔ Этот раздел доступен только администраторам.",
        "en": "⛔ This section is available to administrators only.",
    },
    "admin_panel_title": {
        "uz": "🛠 Admin Panel",
        "ru": "🛠 Admin Panel",
        "en": "🛠 Admin Panel",
    },
    "admin_stats_card": {
        "uz": (
            "📊 Bot statistikasi\n\n"
            "👥 Foydalanuvchilar: {users}\n"
            "⬇️ Yuklab olishlar: {downloads}\n"
            "⭐ Sevimlilar: {favorites}"
        ),
        "ru": (
            "📊 Статистика бота\n\n"
            "👥 Пользователи: {users}\n"
            "⬇️ Загрузки: {downloads}\n"
            "⭐ Избранное: {favorites}"
        ),
        "en": (
            "📊 Bot statistics\n\n"
            "👥 Users: {users}\n"
            "⬇️ Downloads: {downloads}\n"
            "⭐ Favorites: {favorites}"
        ),
    },
}


def tr(key: str, lang: str, **kwargs: object) -> str:
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"
    value = TEXTS.get(key, {}).get(lang) or TEXTS.get(key, {}).get("en") or key
    if kwargs:
        return value.format(**kwargs)
    return value
