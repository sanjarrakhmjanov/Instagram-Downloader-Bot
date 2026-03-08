import asyncio
import json
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
        return "□□□□□□□□□□ ~ ..."
    filled = pct // 10
    bar = "■" * filled + "□" * (10 - filled)
    return f"{bar} ~ {pct}%"


def _display_url(raw_url: str) -> str:
    parts = urlsplit(raw_url)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


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


def _fps_from_rate(rate: str | None) -> float | None:
    if not rate or rate in {"0/0", "N/A"}:
        return None
    if "/" in rate:
        num, den = rate.split("/", 1)
        try:
            den_v = float(den)
            if den_v == 0:
                return None
            return float(num) / den_v
        except ValueError:
            return None
    try:
        return float(rate)
    except ValueError:
        return None


def _probe_media(path: Path, ffprobe_path: str | None) -> dict | None:
    if not ffprobe_path:
        return None
    cmd = [
        ffprobe_path,
        "-v",
        "error",
        "-show_streams",
        "-show_format",
        "-print_format",
        "json",
        str(path),
    ]
    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            text=True,
        )
    except Exception:
        return None
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


def _extract_video_meta(probe: dict | None) -> tuple[int | None, int | None, int | None]:
    if not probe:
        return None, None, None
    width = height = duration = None
    for stream in probe.get("streams", []):
        if stream.get("codec_type") == "video":
            with suppress(Exception):
                width = int(stream.get("width")) if stream.get("width") else None
            with suppress(Exception):
                height = int(stream.get("height")) if stream.get("height") else None
            break
    raw_dur = (probe.get("format") or {}).get("duration")
    with suppress(Exception):
        if raw_dur is not None:
            duration = max(0, int(float(raw_dur)))
    return width, height, duration


def _is_telegram_video_compatible(probe: dict | None) -> bool:
    if not probe:
        return False

    fmt = (probe.get("format") or {}).get("format_name", "")
    streams = probe.get("streams", [])
    v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)
    if not v_stream:
        return False

    vcodec = (v_stream.get("codec_name") or "").lower()
    pix_fmt = (v_stream.get("pix_fmt") or "").lower()
    fps = _fps_from_rate(v_stream.get("avg_frame_rate"))
    width = int(v_stream.get("width") or 0)
    height = int(v_stream.get("height") or 0)
    acodec = (a_stream.get("codec_name") or "").lower() if a_stream else ""

    return (
        "mp4" in fmt
        and vcodec == "h264"
        and (not acodec or acodec == "aac")
        and pix_fmt == "yuv420p"
        and width > 0
        and height > 0
        and (fps is None or fps <= 60)
    )


async def _remux_faststart(path: Path, ffmpeg_path: str | None) -> Path:
    if not ffmpeg_path:
        return path
    remuxed = path.with_name(f"{path.stem}.faststart.mp4")
    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(path),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(remuxed),
    ]

    def _run() -> int:
        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode

    code = await asyncio.to_thread(_run)
    if code != 0 or not remuxed.exists() or remuxed.stat().st_size == 0:
        with suppress(Exception):
            if remuxed.exists():
                remuxed.unlink()
        return path
    return remuxed


async def _compress_to_target_size(
    path: Path,
    ffmpeg_path: str | None,
    duration_sec: int | None,
    max_bytes: int,
) -> Path:
    if not ffmpeg_path or not duration_sec or duration_sec <= 0:
        return path

    audio_bitrate = 96_000
    target_total_bps = int((max_bytes * 8) / duration_sec * 0.92)
    video_bitrate = max(250_000, target_total_bps - audio_bitrate)
    compressed = path.with_name(f"{path.stem}.compressed.mp4")

    cmd = [
        ffmpeg_path,
        "-y",
        "-i",
        str(path),
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "baseline",
        "-level",
        "3.0",
        "-r",
        "30",
        "-vsync",
        "cfr",
        "-b:v",
        str(video_bitrate),
        "-maxrate",
        str(int(video_bitrate * 1.2)),
        "-bufsize",
        str(int(video_bitrate * 2.0)),
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(compressed),
    ]

    def _run() -> int:
        return subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        ).returncode

    code = await asyncio.to_thread(_run)
    if code != 0 or not compressed.exists() or compressed.stat().st_size == 0:
        with suppress(Exception):
            if compressed.exists():
                compressed.unlink()
        return path
    return compressed


async def worker() -> None:
    settings = get_settings()
    setup_json_logging(settings.log_level)
    await init_db()

    ffmpeg_bin = settings.ffmpeg_path or shutil.which("ffmpeg")
    ffprobe_bin = shutil.which("ffprobe")
    if not ffmpeg_bin:
        logger.warning("ffmpeg not found, mobile video compatibility conversion is disabled")
    if not ffprobe_bin:
        logger.warning("ffprobe not found, media probe validation is limited")

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
        await queue.set_active_job(job.user_id, job.request_id, ttl_sec=settings.request_timeout_sec)

        status_msg = await bot.send_message(
            chat_id=job.chat_id,
            text=tr("processing", job.language, progress=_render_progress("0")),
        )
        result = None
        generated_paths: list[Path] = []

        cancel_requested = False

        async def on_progress(progress_text: str) -> None:
            with suppress(Exception):
                await bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=status_msg.message_id,
                    text=tr("processing", job.language, progress=_render_progress(progress_text)),
                )

        async def watch_cancel() -> None:
            nonlocal cancel_requested
            while True:
                await asyncio.sleep(1)
                if await queue.is_cancel_requested(job.request_id):
                    cancel_requested = True
                    return

        cancel_task = asyncio.create_task(watch_cancel())

        def _cancel_check() -> bool:
            return cancel_requested

        try:
            result = await downloader.download(
                job.url,
                job.option,
                progress_cb=on_progress,
                cancel_check=_cancel_check,
            )
            if cancel_requested:
                raise asyncio.CancelledError("Cancelled by user")
            if not result.file_path.exists():
                raise FileNotFoundError("Downloaded file not found")
            max_size_bytes = settings.max_file_size_mb * 1024 * 1024

            caption = f"{escape(result.title)}\n{escape(_display_url(job.url))}"
            if result.media_kind == "audio":
                if result.file_path.stat().st_size > max_size_bytes:
                    await bot.edit_message_text(
                        chat_id=job.chat_id,
                        message_id=status_msg.message_id,
                        text="Audio file too large for Telegram upload.",
                    )
                    continue
                await bot.send_audio(
                    chat_id=job.chat_id,
                    audio=FSInputFile(str(result.file_path)),
                    caption=caption,
                )
            elif result.media_kind == "video":
                promo_line = tr("promo_line", job.language)
                probe_before = _probe_media(result.file_path, ffprobe_bin)
                logger.info(
                    "Video probe before processing",
                    extra={
                        "request_id": job.request_id,
                        "file": str(result.file_path),
                        "size_bytes": result.file_path.stat().st_size,
                        "probe_ok": bool(probe_before),
                    },
                )

                video_path = result.file_path
                if _is_telegram_video_compatible(probe_before):
                    remuxed = await _remux_faststart(video_path, ffmpeg_bin)
                    if remuxed != video_path:
                        generated_paths.append(remuxed)
                        video_path = remuxed
                else:
                    converted = await _ensure_mobile_compatible_video(video_path, ffmpeg_bin)
                    if converted != video_path:
                        generated_paths.append(converted)
                        video_path = converted

                if video_path.stat().st_size > max_size_bytes:
                    duration_for_compress = result.duration_sec
                    if not duration_for_compress:
                        _, _, duration_for_compress = _extract_video_meta(_probe_media(video_path, ffprobe_bin))
                    compressed = await _compress_to_target_size(
                        video_path,
                        ffmpeg_bin,
                        duration_for_compress,
                        max_size_bytes,
                    )
                    if compressed != video_path:
                        generated_paths.append(compressed)
                        video_path = compressed

                if video_path.stat().st_size > max_size_bytes:
                    await bot.edit_message_text(
                        chat_id=job.chat_id,
                        message_id=status_msg.message_id,
                        text="Video file too large for Telegram upload.",
                    )
                    continue

                probe_after = _probe_media(video_path, ffprobe_bin)
                width, height, duration = _extract_video_meta(probe_after)
                logger.info(
                    "Video ready for Telegram",
                    extra={
                        "request_id": job.request_id,
                        "file": str(video_path),
                        "size_bytes": video_path.stat().st_size,
                        "width": width,
                        "height": height,
                        "duration": duration,
                        "compatible": _is_telegram_video_compatible(probe_after),
                    },
                )
                if cancel_requested:
                    raise asyncio.CancelledError("Cancelled by user")

                try:
                    await bot.send_video(
                        chat_id=job.chat_id,
                        video=FSInputFile(str(video_path)),
                        caption=f"{caption}\n\n{promo_line}",
                        supports_streaming=True,
                        width=width,
                        height=height,
                        duration=duration or result.duration_sec,
                    )
                    logger.info("Delivery method: send_video", extra={"request_id": job.request_id})
                except TelegramBadRequest:
                    await bot.send_document(
                        chat_id=job.chat_id,
                        document=FSInputFile(str(video_path)),
                        caption=f"{caption}\n\n{promo_line}",
                    )
                    logger.warning("Delivery fallback: send_document", extra={"request_id": job.request_id})
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
            await bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=status_msg.message_id,
                text=tr("done", job.language),
                reply_markup=favorite_keyboard_localized(row.id, job.language),
            )
        except asyncio.CancelledError:
            with suppress(Exception):
                await bot.edit_message_text(
                    chat_id=job.chat_id,
                    message_id=status_msg.message_id,
                    text=tr("flow_cancelled", job.language),
                )
        except Exception as exc:
            fail_key = "failed"
            msg = str(exc).lower()
            if "cancelled by user" in msg:
                fail_key = "flow_cancelled"
            else:
                logger.exception("Download job failed", extra={"request_id": job.request_id, "url": job.url})
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
                cancel_task.cancel()
                with suppress(asyncio.CancelledError):
                    await cancel_task
                for p in generated_paths:
                    if p.exists():
                        p.unlink()
                if result and result.file_path.exists():
                    result.file_path.unlink()
                if result and result.file_path.parent.exists():
                    result.file_path.parent.rmdir()
                await queue.clear_cancel_request(job.request_id)
                await queue.clear_active_job(job.user_id)


if __name__ == "__main__":
    asyncio.run(worker())
