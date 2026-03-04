import asyncio
import logging
import shutil
import subprocess
from contextlib import suppress
from html import escape
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import FSInputFile
from redis.asyncio import Redis

from bot.config import get_settings
from bot.db.repo import DownloadRepository
from bot.db.session import SessionLocal, init_db
from bot.i18n import tr
from bot.json_logger import setup_json_logging
from bot.keyboards.common import favorite_keyboard_localized
from bot.services.downloader import DownloaderService
from bot.services.queue import QueueService

logger = logging.getLogger(__name__)


def _render_progress(progress_text: str) -> str:
    clean = progress_text.strip().replace("%", "")
    try:
        pct = max(0, min(100, int(float(clean))))
    except ValueError:
        return "[..........] ..."
    filled = pct // 10
    bar = "#" * filled + "." * (10 - filled)
    return f"[{bar}] {pct}%"


def _display_url(raw_url: str) -> str:
    parts = urlsplit(raw_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def _format_label(media_kind: str, option: str) -> str:
    if media_kind == "photo":
        return "IMAGE"
    if media_kind == "video":
        return "VIDEO"
    if media_kind == "audio":
        return "MP3" if option == "mp3" else "AUDIO"
    return "FILE"


async def _ensure_mobile_compatible_video(path: Path, ffmpeg_path: str | None) -> Path:
    if not ffmpeg_path:
        return path
    converted = path.with_name(f"{path.stem}.mobile.mp4")
    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(path),
        "-vf",
        # Strict compatibility profile for older Telegram mobile decoders.
        "scale='min(1280,iw)':-2:flags=lanczos,fps=30,format=yuv420p",
        "-vsync",
        "cfr",
        "-r",
        "30",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "baseline",
        "-level",
        "3.0",
        "-x264-params",
        "keyint=60:min-keyint=60:scenecut=0",
        "-preset",
        "veryfast",
        "-crf",
        "24",
        "-maxrate",
        "2500k",
        "-bufsize",
        "5000k",
        "-g",
        "60",
        "-c:a",
        "aac",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-b:a",
        "96k",
        "-max_muxing_queue_size",
        "2048",
        "-movflags",
        "+faststart",
        str(converted),
    ]

    def _run() -> int:
        proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        return proc.returncode

    code = await asyncio.to_thread(_run)
    if code != 0 or not converted.exists() or converted.stat().st_size == 0:
        with suppress(Exception):
            if converted.exists():
                converted.unlink()
        return path
    return converted


async def worker() -> None:
    settings = get_settings()
    setup_json_logging(settings.log_level)
    await init_db()

    ffmpeg_bin = settings.ffmpeg_path or shutil.which("ffmpeg")
    if not ffmpeg_bin:
        logger.warning("ffmpeg not found, mobile video compatibility conversion is disabled")

    redis = Redis.from_url(settings.redis_dsn, decode_responses=True)
    queue = QueueService(redis)
    downloader = DownloaderService(
        settings.download_dir,
        settings.request_timeout_sec,
        ffmpeg_location=ffmpeg_bin,
    )
    bot = Bot(token=settings.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))

    logger.info("Worker started")
    while True:
        job = await queue.dequeue(timeout=5)
        if not job:
            continue

        status_msg = await bot.send_message(
            chat_id=job.chat_id,
            text=tr("processing", job.language, progress=_render_progress("0")),
        )
        result = None
        generated_paths: list[Path] = []

        async def on_progress(progress_text: str) -> None:
            with suppress(Exception):
                await bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=status_msg.message_id,
                    text=tr("processing", job.language, progress=_render_progress(progress_text)),
                )

        try:
            result = await downloader.download(job.url, job.option, progress_cb=on_progress)
            if not result.file_path.exists():
                raise FileNotFoundError("Downloaded file not found")
            max_size_bytes = settings.max_file_size_mb * 1024 * 1024
            if result.file_path.stat().st_size > max_size_bytes:
                await bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=status_msg.message_id,
                    text="File too large for Telegram upload.",
                )
                continue

            caption = f"{escape(result.title)}\n{escape(_display_url(job.url))}"
            if result.media_kind == "audio":
                await bot.send_audio(
                    chat_id=job.chat_id,
                    audio=FSInputFile(str(result.file_path)),
                    caption=caption,
                )
            elif result.media_kind == "video":
                video_path = await _ensure_mobile_compatible_video(
                    result.file_path, ffmpeg_bin
                )
                if video_path != result.file_path:
                    generated_paths.append(video_path)
                await bot.send_video(
                    chat_id=job.chat_id,
                    video=FSInputFile(str(video_path)),
                    caption=caption,
                    supports_streaming=True,
                )
            elif result.media_kind == "photo":
                try:
                    await bot.send_photo(
                        chat_id=job.chat_id,
                        photo=FSInputFile(str(result.file_path)),
                        caption=caption,
                    )
                except TelegramBadRequest:
                    # Fallback for large/unusual image files.
                    await bot.send_document(
                        chat_id=job.chat_id,
                        document=FSInputFile(str(result.file_path)),
                        caption=caption,
                    )
            else:
                await bot.send_document(
                    chat_id=job.chat_id,
                    document=FSInputFile(str(result.file_path)),
                    caption=caption,
                )

            async with SessionLocal() as session:
                repo = DownloadRepository(session)
                row = await repo.add_download(
                    tg_user_id=job.user_id,
                    platform=job.platform,
                    url=job.url,
                    title=result.title,
                    selected_format=job.option,
                    duration_sec=result.duration_sec,
                )
                await bot.send_message(
                    chat_id=job.chat_id,
                    text=tr(
                        "completed_card",
                        job.language,
                        title=escape(result.title),
                        fmt=escape(_format_label(result.media_kind, job.option)),
                    ),
                    reply_markup=favorite_keyboard_localized(row.id, job.language),
                )
            await bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=status_msg.message_id,
                text=tr("done", job.language),
            )
        except Exception as exc:
            logger.exception("Download job failed", extra={"request_id": job.request_id, "url": job.url})
            fail_key = "failed"
            msg = str(exc).lower()
            if "there is no video in this post" in msg:
                fail_key = "source_unavailable"
            elif "instagram" in msg and ("login required" in msg or "restricted" in msg or "private" in msg):
                fail_key = "instagram_restricted"
            elif "no downloadable file was created" in msg:
                fail_key = "source_unavailable"
            elif "not found" in msg or "404" in msg or "unavailable" in msg:
                fail_key = "source_unavailable"
            elif job.platform == "instagram":
                # Instagram often returns generic extraction errors for restricted posts.
                fail_key = "instagram_restricted"
            with suppress(Exception):
                await bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=status_msg.message_id,
                    text=tr(fail_key, job.language),
                )
        finally:
            with suppress(Exception):
                for p in generated_paths:
                    if p.exists():
                        p.unlink()
                if result and result.file_path.exists():
                    result.file_path.unlink()
                if result and result.file_path.parent.exists():
                    result.file_path.parent.rmdir()


if __name__ == "__main__":
    asyncio.run(worker())
