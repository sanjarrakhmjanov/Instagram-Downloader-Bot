SUPPORTED_LANGUAGES = ("uz", "ru", "en")
QUEUE_KEY = "downloads:queue"
PENDING_REQUEST_KEY = "downloads:pending:{request_id}"
RATE_LIMIT_KEY = "rate_limit:{user_id}"
ACTIVE_JOB_KEY = "downloads:active:{user_id}"
CANCEL_REQUEST_KEY = "downloads:cancel:{request_id}"

DOWNLOAD_OPTIONS = {
    "video": {"label": "VIDEO", "yt_format": "bestvideo+bestaudio/best"},
    "mp3": {"label": "MP3", "yt_format": "bestaudio/best"},
}
