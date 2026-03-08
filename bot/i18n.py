from bot.constants import SUPPORTED_LANGUAGES

TEXTS = {
    "start": {
        "uz": (
            "🚀 @saveviathisbot orqali Instagram video va MP3 ni tez yuklab oling!\n\n"
            "Instagram Downloader botiga xush kelibsiz.\n\n"
            "Qo'llab-quvvatlanadi:\n"
            "- Instagram Reels\n"
            "- Instagram Posts (video/rasm)\n\n"
            "Ishlash tartibi:\n"
            "1) Instagram havola yuboring\n"
            "2) Video yoki MP3 tanlang (post rasm bo'lsa avtomatik)\n"
            "3) Faylni qabul qiling"
        ),
        "ru": (
            "🚀 Быстро скачивайте Instagram видео и MP3 через @saveviathisbot!\n\n"
            "Добро пожаловать в Instagram Downloader.\n\n"
            "Поддерживается:\n"
            "- Instagram Reels\n"
            "- Instagram Posts (видео/фото)\n\n"
            "Как это работает:\n"
            "1) Отправьте ссылку Instagram\n"
            "2) Выберите Video или MP3 (для фото-поста автоматом)\n"
            "3) Получите файл"
        ),
        "en": (
            "🚀 Download Instagram videos and MP3 quickly via @saveviathisbot!\n\n"
            "Welcome to Instagram Downloader.\n\n"
            "Supported:\n"
            "- Instagram Reels\n"
            "- Instagram Posts (video/photo)\n\n"
            "How it works:\n"
            "1) Send an Instagram link\n"
            "2) Choose Video or MP3 (auto for image posts)\n"
            "3) Receive your file"
        ),
    },
    "promo_line": {
        "uz": "🚀 @saveviathisbot orqali Instagram video va MP3 ni tez yuklab oling!",
        "ru": "🚀 Быстро скачивайте Instagram видео и MP3 через @saveviathisbot!",
        "en": "🚀 Download Instagram videos and MP3 quickly via @saveviathisbot!",
    },
    "help": {
        "uz": "Instagram havola yuboring. Video yoki MP3 tanlang. Post rasm bo'lsa avtomatik yuboriladi.",
        "ru": "Отправьте ссылку Instagram. Выберите Video или MP3. Фото-пост отправляется автоматически.",
        "en": "Send an Instagram link. Choose Video or MP3. Image posts are sent automatically.",
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
        "uz": "⏳ Qabul qilindi. Navbat: #{position}",
        "ru": "⏳ Принято. Очередь: #{position}",
        "en": "⏳ Accepted. Queue: #{position}",
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
        "uz": "✅ Tayyor.",
        "ru": "✅ Готово.",
        "en": "✅ Done.",
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
            "👋 Xush kelibsiz.\n\n"
            "Bot interfeysi tilini tanlang.\n"
            "Keyin asosiy menyu avtomatik ochiladi."
        ),
        "ru": (
            "👋 Добро пожаловать.\n\n"
            "Выберите язык интерфейса бота.\n"
            "После этого откроется главное меню."
        ),
        "en": (
            "👋 Welcome.\n\n"
            "Choose the bot interface language.\n"
            "The main menu will open right after."
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
    "menu_privacy": {
        "uz": "🔒 Maxfiylik",
        "ru": "🔒 Приватность",
        "en": "🔒 Privacy",
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
    "privacy": {
        "uz": "Biz faqat xizmat uchun zarur bo'lgan ma'lumotlarni saqlaymiz.",
        "ru": "Мы храним только данные, необходимые для работы сервиса.",
        "en": "We only store data required to provide the service.",
    },
    "history_empty": {
        "uz": "Tarix bo'sh.",
        "ru": "История пуста.",
        "en": "History is empty.",
    },
    "favorites_empty": {
        "uz": "Sevimlilar bo'sh.",
        "ru": "Избранное пусто.",
        "en": "Favorites are empty.",
    },
    "saved_to_favorites": {
        "uz": "Sevimlilarga saqlandi.",
        "ru": "Сохранено в избранное.",
        "en": "Saved to favorites.",
    },
    "favorite_button": {
        "uz": "⭐ Sevimli",
        "ru": "⭐ В избранное",
        "en": "⭐ Favorite",
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
