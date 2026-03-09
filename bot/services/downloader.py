import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
from collections import OrderedDict
import urllib.request
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

import yt_dlp
from yt_dlp.utils import DownloadError

from bot.constants import DOWNLOAD_OPTIONS
from bot.services.safe_files import safe_basename

logger = logging.getLogger(__name__)


class YtdlpLogAdapter:
    _ansi_re = re.compile(r"\x1b\[[0-9;]*m")
    _error_prefix_re = re.compile(r"^(ERROR:\s*)+", flags=re.IGNORECASE)

    @classmethod
    def _clean(cls, msg: str) -> str:
        cleaned = cls._ansi_re.sub("", msg).strip()
        return cls._error_prefix_re.sub("", cleaned).strip()

    def debug(self, msg: str) -> None:
        cleaned = self._clean(msg)
        if cleaned:
            logger.debug(cleaned)

    def warning(self, msg: str) -> None:
        cleaned = self._clean(msg)
        if cleaned:
            logger.warning(cleaned)

    def error(self, msg: str) -> None:
        cleaned = self._clean(msg)
        if cleaned:
            if "there is no video in this post" in cleaned.lower():
                logger.warning(cleaned)
            else:
                logger.error(cleaned)


@dataclass
class MediaMetadata:
    title: str
    duration_sec: int | None
    webpage_url: str


@dataclass
class DownloadResult:
    file_paths: list[Path]
    title: str
    duration_sec: int | None
    option: str
    media_kind: str


class DownloaderService:
    def __init__(
        self,
        output_dir: str,
        timeout_sec: int = 900,
        ffmpeg_location: str | None = None,
        instagram_cookies_file: str | None = None,
    ):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timeout_sec = timeout_sec
        self.ffmpeg_location = ffmpeg_location or shutil.which("ffmpeg")
        self.instagram_cookies_file = instagram_cookies_file

    def _apply_common_ytdlp_options(self, options: dict[str, Any], url: str | None = None) -> None:
        options["no_warnings"] = True
        options["logger"] = YtdlpLogAdapter()
        options["http_headers"] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }
        if (
            url
            and "instagram.com" in url.lower()
            and self.instagram_cookies_file
            and Path(self.instagram_cookies_file).exists()
        ):
            options["cookiefile"] = self.instagram_cookies_file

    @staticmethod
    def _classify_media(path: Path, option: str) -> str:
        if option == "mp3":
            return "audio"
        ext = path.suffix.lower()
        if ext in {".jpg", ".jpeg", ".png", ".webp", ".bmp"}:
            return "photo"
        if ext in {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi"}:
            return "video"
        if ext in {".mp3", ".m4a", ".aac", ".ogg", ".wav", ".flac"}:
            return "audio"
        return "document"

    @staticmethod
    def _find_requested_filepaths(info: dict[str, Any]) -> list[Path]:
        found: list[Path] = []

        def _append_if_exists(fp: str | None) -> None:
            if not fp:
                return
            p = Path(fp)
            if p.exists() and p not in found:
                found.append(p)

        for item in info.get("requested_downloads") or []:
            _append_if_exists(item.get("filepath") or item.get("_filename"))
        for entry in info.get("entries") or []:
            for item in entry.get("requested_downloads") or []:
                _append_if_exists(item.get("filepath") or item.get("_filename"))
            _append_if_exists(entry.get("_filename"))
        _append_if_exists(info.get("_filename"))
        return found

    @staticmethod
    def _extract_direct_media_urls(info: dict[str, Any]) -> list[tuple[str, str, str]]:
        candidates: list[dict[str, Any]] = [info]
        for entry in info.get("entries") or []:
            if isinstance(entry, dict):
                candidates.append(entry)

        seen: set[str] = set()
        picked: list[tuple[str, str, str]] = []
        for item in candidates:
            url = item.get("url")
            ext = str(item.get("ext") or "").lower()
            title = str(item.get("title") or info.get("title") or "media")
            if not url:
                continue
            if ext not in {"jpg", "jpeg", "png", "webp", "bmp", "mp4"}:
                continue
            u = str(url)
            if u in seen:
                continue
            seen.add(u)
            picked.append((u, f".{ext}", title))
        return picked

    @staticmethod
    def _extract_og_tag(html_text: str, prop: str) -> str | None:
        pattern = re.compile(
            rf'<meta[^>]+property=["\']{re.escape(prop)}["\'][^>]+content=["\']([^"\']+)["\']',
            flags=re.IGNORECASE,
        )
        match = pattern.search(html_text)
        return unescape(match.group(1)) if match else None

    def _fetch_instagram_page(self, page_url: str) -> str:
        req = urllib.request.Request(
            page_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    def _fallback_instagram_og_metadata(self, page_url: str) -> MediaMetadata | None:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return None
        title = self._extract_og_tag(html_text, "og:title") or "Instagram media"
        return MediaMetadata(title=title, duration_sec=None, webpage_url=page_url)

    def _fallback_instagram_og_asset(self, page_url: str, target_dir: Path) -> Path | None:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return None
        media_url = self._extract_og_tag(html_text, "og:video") or self._extract_og_tag(html_text, "og:image")
        if not media_url:
            # Fallback for pages where OG tags are missing but inline JSON still contains media URLs.
            video_match = re.search(r'"video_url":"([^"]+)"', html_text)
            image_match = re.search(r'"display_url":"([^"]+)"', html_text)
            raw = video_match.group(1) if video_match else (image_match.group(1) if image_match else "")
            if raw:
                media_url = (
                    raw.replace("\\/", "/")
                    .replace("\\u0026", "&")
                    .replace("\\u0025", "%")
                )
        if not media_url:
            return None
        suffix = ".mp4" if ".mp4" in media_url.lower() else ".jpg"
        target = target_dir / f"instagram_fallback{suffix}"
        try:
            urllib.request.urlretrieve(media_url, target)
        except Exception:
            return None
        return target if target.exists() and target.stat().st_size > 0 else None

    @staticmethod
    def _decode_escaped_url(raw: str) -> str:
        return (
            raw.replace("\\/", "/")
            .replace("\\u0026", "&")
            .replace("\\u0025", "%")
            .replace("\\\\", "\\")
        )

    @staticmethod
    def _is_probable_instagram_media_url(url: str) -> bool:
        lower = url.lower()
        # Keep only probable Instagram CDN media URLs, skip generic page assets/icons/badges.
        return (
            (".cdninstagram.com" in lower or ".fbcdn.net" in lower or "scontent" in lower)
            and any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".webp"])
        )

    def _fallback_instagram_gallery_assets(self, page_url: str, target_dir: Path) -> list[Path]:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return []

        # Collect multiple unique image urls for carousel/photo posts.
        found: "OrderedDict[str, None]" = OrderedDict()
        patterns = [
            r'"display_url":"([^"]+)"',
            r'"display_src":"([^"]+)"',
            r'"thumbnail_src":"([^"]+)"',
            r'"image_versions2":\{"candidates":\[\{"url":"([^"]+)"',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, html_text):
                url = self._decode_escaped_url(m.group(1))
                if url.startswith("http") and self._is_probable_instagram_media_url(url):
                    found.setdefault(url, None)

        paths: list[Path] = []
        for idx, url in enumerate(found.keys(), 1):
            ext = ".jpg"
            low = url.lower()
            if ".png" in low:
                ext = ".png"
            elif ".webp" in low:
                ext = ".webp"
            target = target_dir / f"instagram_gallery_{idx:03d}{ext}"
            try:
                urllib.request.urlretrieve(url, target)
            except Exception:
                continue
            if target.exists() and target.stat().st_size > 0:
                paths.append(target)
        return paths

    def _fallback_instagram_oembed_asset(self, page_url: str, target_dir: Path) -> Path | None:
        normalized = page_url if page_url.endswith("/") else f"{page_url}/"
        api_url = f"https://www.instagram.com/api/v1/oembed/?url={quote(normalized, safe=':/?=&')}"
        req = urllib.request.Request(
            api_url,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
        except Exception:
            return None

        thumb_url = data.get("thumbnail_url")
        if not thumb_url:
            return None
        ext = ".jpg"
        low = str(thumb_url).lower()
        if ".png" in low:
            ext = ".png"
        elif ".webp" in low:
            ext = ".webp"

        target = target_dir / f"instagram_oembed{ext}"
        try:
            urllib.request.urlretrieve(str(thumb_url), target)
        except Exception:
            return None
        return target if target.exists() and target.stat().st_size > 0 else None

    @staticmethod
    def _download_direct_media_assets(info: dict[str, Any], target_dir: Path) -> list[Path]:
        items = DownloaderService._extract_direct_media_urls(info)
        if not items:
            return []

        paths: list[Path] = []
        for idx, (asset_url, suffix, title) in enumerate(items, 1):
            target = target_dir / f"{safe_basename(title)}_{idx:03d}{suffix}"
            try:
                urllib.request.urlretrieve(asset_url, target)
            except Exception:
                continue
            if target.exists() and target.stat().st_size > 0:
                paths.append(target)
        return paths

    async def fetch_metadata(self, url: str) -> MediaMetadata:
        def _extract() -> dict[str, Any]:
            options: dict[str, Any] = {"quiet": True, "skip_download": True, "noplaylist": True}
            if self.ffmpeg_location:
                options["ffmpeg_location"] = self.ffmpeg_location
            self._apply_common_ytdlp_options(options, url=url)
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=False)

        try:
            info = await asyncio.wait_for(asyncio.to_thread(_extract), timeout=self.timeout_sec)
        except Exception:
            fallback = await asyncio.to_thread(self._fallback_instagram_og_metadata, url)
            if fallback:
                return fallback
            raise

        duration = info.get("duration")
        duration_int = int(duration) if isinstance(duration, (int, float)) else None
        return MediaMetadata(
            title=info.get("title") or "Untitled",
            duration_sec=duration_int,
            webpage_url=info.get("webpage_url") or url,
        )

    async def download(
        self,
        url: str,
        option: str,
        progress_cb: Callable[[str], Any] | None = None,
        cancel_check: Callable[[], bool] | None = None,
    ) -> DownloadResult:
        if option not in DOWNLOAD_OPTIONS:
            raise ValueError(f"Unsupported option: {option}")

        download_dir = self.output_dir / safe_basename(str(asyncio.get_running_loop().time()))
        download_dir.mkdir(parents=True, exist_ok=True)
        progress = {"text": "0%"}

        def _hook(status: dict[str, Any]) -> None:
            if cancel_check and cancel_check():
                raise DownloadError("Cancelled by user")
            if status.get("status") == "downloading":
                total = status.get("total_bytes") or status.get("total_bytes_estimate") or 0
                downloaded = status.get("downloaded_bytes") or 0
                if total:
                    pct = int(downloaded * 100 / total)
                    progress["text"] = f"{max(0, min(100, pct))}%"
                else:
                    raw = str(status.get("_percent_str", "")).strip()
                    m = re.search(r"(\d+(?:\.\d+)?)", raw)
                    progress["text"] = f"{m.group(1)}%" if m else progress["text"]

        def _download() -> tuple[list[str], dict[str, Any]]:
            is_instagram_post = "instagram.com/p/" in url.lower()
            outtmpl = str(download_dir / "%(title).100B.%(ext)s")
            base_options: dict[str, Any] = {
                "outtmpl": outtmpl,
                # Keep full carousel extraction for Instagram posts.
                "noplaylist": not is_instagram_post,
                "quiet": True,
                "progress_hooks": [_hook],
                "noprogress": True,
                "retries": 3,
                "continuedl": True,
                "postprocessor_args": ["-movflags", "+faststart"],
            }
            if self.ffmpeg_location:
                base_options["ffmpeg_location"] = self.ffmpeg_location
            self._apply_common_ytdlp_options(base_options, url=url)
            if option == "mp3":
                base_options["postprocessors"] = [
                    {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}
                ]
            else:
                if not is_instagram_post:
                    # Improve mobile playback compatibility for direct video links.
                    base_options["merge_output_format"] = "mp4"
                    base_options["postprocessors"] = [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}]

            format_attempts: list[str | None]
            if option == "mp3":
                format_attempts = ["bestaudio/best", "best", None]
            else:
                if is_instagram_post:
                    # For /p/ posts (including carousel), keep original media entries and avoid video-only filter.
                    format_attempts = ["best", None]
                else:
                    format_attempts = [
                        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]",
                        "best[ext=mp4]/bestvideo+bestaudio/best",
                        "best",
                        None,
                    ]

            last_error: Exception | None = None
            for fmt in format_attempts:
                if cancel_check and cancel_check():
                    raise DownloadError("Cancelled by user")
                options = dict(base_options)
                if fmt:
                    options["format"] = fmt
                try:
                    with yt_dlp.YoutubeDL(options) as ydl:
                        info = ydl.extract_info(url, download=True)
                        logger.info(
                            "Download extracted",
                            extra={
                                "selected_format": fmt or "auto",
                                "ext": info.get("ext"),
                                "vcodec": info.get("vcodec"),
                                "acodec": info.get("acodec"),
                                "duration": info.get("duration"),
                            },
                        )
                        if option == "mp3":
                            prepared = ydl.prepare_filename(info)
                            return [str(Path(prepared).with_suffix(".mp3"))], info
                        requested_paths = self._find_requested_filepaths(info)
                        if requested_paths:
                            return [str(p) for p in requested_paths], info
                        prepared = ydl.prepare_filename(info)
                        if Path(prepared).exists():
                            return [prepared], info
                        direct_assets = self._download_direct_media_assets(info, download_dir)
                        if direct_assets:
                            return [str(p) for p in direct_assets], info
                        raise DownloadError("Extractor returned metadata but no downloadable file was created")
                except DownloadError as exc:
                    last_error = exc
                    err = str(exc).lower()
                    if "requested format is not available" in err:
                        logger.warning("Format unavailable, trying fallback")
                        continue
                    if "no downloadable file was created" in err:
                        logger.warning("No file produced, trying next fallback")
                        continue
                    if "there is no video in this post" in err:
                        # Common for Instagram image posts; let OG-image fallback handle it.
                        logger.warning("Instagram post has no video, trying image fallback")
                        continue
                    if (
                        "login required" in err
                        or "private" in err
                        or "restricted" in err
                        or "challenge_required" in err
                        or "not authorized" in err
                    ):
                        # Allow HTML/OG fallback chain for public links even when extractor is blocked.
                        logger.warning("Extractor access restricted, trying fallback chain")
                        continue
                    raise

            gallery_assets = self._fallback_instagram_gallery_assets(url, download_dir)
            if gallery_assets:
                return [str(p) for p in gallery_assets], {"title": "Instagram media", "duration": None}

            fallback_asset = self._fallback_instagram_og_asset(url, download_dir)
            if not fallback_asset:
                fallback_asset = self._fallback_instagram_oembed_asset(url, download_dir)
            if fallback_asset:
                return [str(fallback_asset)], {"title": "Instagram media", "duration": None}
            raise last_error or RuntimeError("Failed to download media")

        async def _progress_updater() -> None:
            if not progress_cb:
                return
            last = None
            while True:
                await asyncio.sleep(0.3)
                if progress["text"] != last:
                    last = progress["text"]
                    await progress_cb(last)

        progress_task = asyncio.create_task(_progress_updater())
        try:
            file_paths, info = await asyncio.wait_for(asyncio.to_thread(_download), timeout=self.timeout_sec)
        finally:
            progress_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await progress_task

        if progress_cb:
            await progress_cb("100%")

        resolved_paths: list[Path] = [Path(p) for p in file_paths if Path(p).exists()]
        if not resolved_paths:
            for root, _, files in os.walk(download_dir):
                for name in sorted(files):
                    resolved_paths.append(Path(root) / name)
        if not resolved_paths:
            raise FileNotFoundError("Downloaded file not found")

        duration = info.get("duration")
        duration_int = int(duration) if isinstance(duration, (int, float)) else None
        primary = resolved_paths[0]
        return DownloadResult(
            file_paths=resolved_paths,
            title=info.get("title") or "Untitled",
            duration_sec=duration_int,
            option=option,
            media_kind=self._classify_media(primary, option),
        )
