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

MEDIA_EXT_RE = re.compile(r"\.(mp4|jpg|jpeg|png|webp|bmp)(?:$|[?#])", flags=re.IGNORECASE)


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

    def _extract_instagram_post_info_no_download(self, url: str) -> dict[str, Any] | None:
        options: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "noplaylist": False,
            "extract_flat": False,
            "no_warnings": True,
        }
        if self.ffmpeg_location:
            options["ffmpeg_location"] = self.ffmpeg_location
        self._apply_common_ytdlp_options(options, url=url)
        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                return ydl.extract_info(url, download=False)
        except Exception:
            return None

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
    def _infer_media_ext(url: str, fallback_ext: str | None = None) -> str | None:
        match = MEDIA_EXT_RE.search(url)
        if match:
            return f".{match.group(1).lower()}"
        if fallback_ext:
            ext = fallback_ext.lower().lstrip(".")
            if ext in {"jpg", "jpeg", "png", "webp", "bmp", "mp4"}:
                return f".{ext}"
        return None

    @classmethod
    def _extract_entry_media_url(cls, item: dict[str, Any]) -> tuple[str, str] | None:
        candidates: list[tuple[str, str]] = []

        def _add(url: Any, fallback_ext: str | None = None) -> None:
            if not url:
                return
            u = str(url)
            ext = cls._infer_media_ext(u, fallback_ext)
            if not ext:
                return
            candidates.append((u, ext))

        _add(item.get("url"), str(item.get("ext") or ""))
        _add(item.get("display_url"), "jpg")
        _add(item.get("display_src"), "jpg")
        # Avoid thumbnail/sprite-like assets for strict post fidelity.
        # These can be UI artifacts rather than real post media.

        for fmt in item.get("formats") or []:
            if isinstance(fmt, dict):
                _add(fmt.get("url"), fmt.get("ext"))

        if not candidates:
            return None

        video = next((candidate for candidate in candidates if candidate[1] == ".mp4"), None)
        if video:
            return video

        # Prefer higher quality still image if available, otherwise first valid item.
        for ext in (".jpg", ".jpeg", ".png", ".webp", ".bmp"):
            match = next((candidate for candidate in candidates if candidate[1] == ext), None)
            if match:
                return match
        return candidates[0]

    @classmethod
    def _extract_direct_media_urls(cls, info: dict[str, Any]) -> list[tuple[str, str, str]]:
        entries = [entry for entry in (info.get("entries") or []) if isinstance(entry, dict)]
        candidates: list[dict[str, Any]] = entries or [info]

        seen: set[str] = set()
        picked: list[tuple[str, str, str]] = []
        for item in candidates:
            selected = cls._extract_entry_media_url(item)
            if not selected:
                continue
            media_url, ext = selected
            if media_url in seen:
                continue
            seen.add(media_url)
            picked.append((media_url, ext, str(item.get("title") or info.get("title") or "media")))
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

    def _fallback_instagram_og_asset(
        self,
        page_url: str,
        target_dir: Path,
        *,
        allow_image: bool = True,
    ) -> Path | None:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return None
        media_url = self._extract_og_tag(html_text, "og:video")
        if not media_url and allow_image:
            media_url = self._extract_og_tag(html_text, "og:image")
        if not media_url:
            # Fallback for pages where OG tags are missing but inline JSON still contains media URLs.
            video_match = re.search(r'"video_url":"([^"]+)"', html_text)
            image_match = re.search(r'"display_url":"([^"]+)"', html_text) if allow_image else None
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
        if any(token in lower for token in ["appstore", "google-play", "googleplay", "microsoft", "badge", "sprite"]):
            return False
        if not (".cdninstagram.com" in lower or ".fbcdn.net" in lower or "scontent" in lower):
            return False
        return (
            any(ext in lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".mp4"])
        )

    def _fallback_instagram_html_assets(
        self,
        page_url: str,
        target_dir: Path,
        *,
        prefer_video: bool,
    ) -> list[Path]:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return []

        found: "OrderedDict[str, str]" = OrderedDict()
        video_patterns = [
            r'"video_url":"([^"]+)"',
            r'"contentUrl":"([^"]+\.mp4[^"]*)"',
            r'"video_versions":\[\{[^]]*?"url":"([^"]+)"',
            r'https:\\/\\/[^\"\']+?\.mp4[^\"\']*',
        ]
        image_patterns = [
            r'"display_url":"([^"]+)"',
            r'"display_src":"([^"]+)"',
            r'"thumbnail_src":"([^"]+)"',
            r'"image_versions2":\{"candidates":\[\{"url":"([^"]+)"',
            r'https:\\/\\/[^\"\']+?\.(?:jpg|jpeg|png|webp)[^\"\']*',
        ]
        patterns = video_patterns + image_patterns if prefer_video else image_patterns + video_patterns
        for pattern in patterns:
            for m in re.finditer(pattern, html_text, flags=re.IGNORECASE):
                raw = m.group(1) if m.groups() else m.group(0)
                media_url = self._decode_escaped_url(raw)
                if not (media_url.startswith("http") and self._is_probable_instagram_media_url(media_url)):
                    continue
                low = media_url.lower()
                if ".mp4" in low:
                    found.setdefault(media_url, ".mp4")
                elif ".png" in low:
                    found.setdefault(media_url, ".png")
                elif ".webp" in low:
                    found.setdefault(media_url, ".webp")
                else:
                    found.setdefault(media_url, ".jpg")

        paths: list[Path] = []
        for idx, (u, ext) in enumerate(found.items(), 1):
            if prefer_video and ext != ".mp4":
                continue
            if (not prefer_video) and ext == ".mp4":
                # For post-first fallback keep still media first.
                continue
            target = target_dir / f"instagram_html_{idx:03d}{ext}"
            try:
                urllib.request.urlretrieve(u, target)
            except Exception:
                continue
            if target.exists() and target.stat().st_size > 0:
                if ext != ".mp4" and target.stat().st_size < 40 * 1024:
                    with contextlib.suppress(Exception):
                        target.unlink()
                    continue
                paths.append(target)
        return paths

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
            # Filter out tiny UI assets/icons; keep real media frames/photos.
            if target.exists() and target.stat().st_size >= 40 * 1024:
                paths.append(target)
        return paths

    def _fallback_instagram_post_structured_assets(self, page_url: str, target_dir: Path) -> list[Path]:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return []

        # Strict post-only extraction:
        # - pull only media-like URLs from Instagram CDN
        # - keep only post image bucket (t51.2885-15) to avoid avatars/sprites/assets
        # - dedupe and filter tiny files
        found: "OrderedDict[str, str]" = OrderedDict()
        patterns = [
            r'"image_versions2":\{"candidates":\[\{"url":"([^"]+)"',
            r'"display_url":"([^"]+)"',
            r'"display_resources":\[\{"src":"([^"]+)"',
            r'"thumbnail_src":"([^"]+)"',
            r'"video_url":"([^"]+)"',
            r'"video_versions":\[\{"type":[^]]*?"url":"([^"]+)"',
        ]
        for pattern in patterns:
            for m in re.finditer(pattern, html_text, flags=re.IGNORECASE):
                media_url = self._decode_escaped_url(m.group(1))
                low = media_url.lower()
                if not (media_url.startswith("http") and self._is_probable_instagram_media_url(media_url)):
                    continue
                if "t51.2885-15" not in low and "/vp/" not in low:
                    continue
                ext = ".jpg"
                if ".mp4" in low:
                    ext = ".mp4"
                elif ".png" in low:
                    ext = ".png"
                elif ".webp" in low:
                    ext = ".webp"
                found.setdefault(media_url, ext)

        paths: list[Path] = []
        for idx, (u, ext) in enumerate(found.items(), 1):
            target = target_dir / f"instagram_post_{idx:03d}{ext}"
            try:
                urllib.request.urlretrieve(u, target)
            except Exception:
                continue
            if target.exists() and target.stat().st_size > 0:
                if ext != ".mp4" and target.stat().st_size < 40 * 1024:
                    with contextlib.suppress(Exception):
                        target.unlink()
                    continue
                paths.append(target)
        return paths

    def _fallback_instagram_sidecar_assets(self, page_url: str, target_dir: Path) -> list[Path]:
        try:
            html_text = self._fetch_instagram_page(page_url)
        except Exception:
            return []

        urls: "OrderedDict[str, str]" = OrderedDict()

        # JSON blobs embedded by Instagram often contain sidecar children in this shape:
        # "edge_sidecar_to_children":{"edges":[{"node":{...}}, ...]}
        sidecar_re = re.compile(
            r'"edge_sidecar_to_children"\s*:\s*\{"edges"\s*:\s*\[(.*?)\]\s*\}',
            flags=re.IGNORECASE | re.DOTALL,
        )
        blocks = sidecar_re.findall(html_text)
        for block in blocks:
            node_re = re.compile(r'"node"\s*:\s*\{(.*?)\}(?:,\s*\{|\s*$)', flags=re.DOTALL)
            nodes = node_re.findall(block) or [block]
            for node in nodes:
                # video first
                for m in re.finditer(r'"video_url"\s*:\s*"([^"]+)"', node, flags=re.IGNORECASE):
                    u = self._decode_escaped_url(m.group(1))
                    low = u.lower()
                    if not (u.startswith("http") and self._is_probable_instagram_media_url(u)):
                        continue
                    if "t51.2885-15" not in low and "/vp/" not in low:
                        continue
                    urls.setdefault(u, ".mp4")
                # image variants
                for pat in (
                    r'"display_url"\s*:\s*"([^"]+)"',
                    r'"display_resources"\s*:\s*\[\{"src"\s*:\s*"([^"]+)"',
                    r'"thumbnail_src"\s*:\s*"([^"]+)"',
                ):
                    for m in re.finditer(pat, node, flags=re.IGNORECASE):
                        u = self._decode_escaped_url(m.group(1))
                        low = u.lower()
                        if not (u.startswith("http") and self._is_probable_instagram_media_url(u)):
                            continue
                        if "t51.2885-15" not in low and "/vp/" not in low:
                            continue
                        ext = ".jpg"
                        if ".png" in low:
                            ext = ".png"
                        elif ".webp" in low:
                            ext = ".webp"
                        urls.setdefault(u, ext)

        paths: list[Path] = []
        for idx, (u, ext) in enumerate(urls.items(), 1):
            target = target_dir / f"instagram_sidecar_{idx:03d}{ext}"
            try:
                urllib.request.urlretrieve(u, target)
            except Exception:
                continue
            if target.exists() and target.stat().st_size > 0:
                if ext != ".mp4" and target.stat().st_size < 40 * 1024:
                    with contextlib.suppress(Exception):
                        target.unlink()
                    continue
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
            is_instagram_video_link = ("instagram.com/reel/" in url.lower()) or ("instagram.com/tv/" in url.lower())
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

                        entry_count = len([e for e in (info.get("entries") or []) if isinstance(e, dict)])
                        requested_paths = self._find_requested_filepaths(info)
                        if is_instagram_post and option != "mp3":
                            # For Instagram posts, aggressively gather full carousel even when extractor
                            # materializes only a subset of entries.
                            direct_assets = self._download_direct_media_assets(info, download_dir)
                            merged: list[Path] = []
                            seen: set[str] = set()
                            for p in [*requested_paths, *direct_assets]:
                                ps = str(p.resolve()) if p.exists() else str(p)
                                if ps in seen:
                                    continue
                                seen.add(ps)
                                if p.exists() and p.stat().st_size > 0:
                                    merged.append(p)

                            if len(merged) > 1:
                                logger.info(
                                    "Instagram post carousel assembled",
                                    extra={"entry_count": entry_count, "asset_count": len(merged)},
                                )
                                return [str(p) for p in merged], info

                            if entry_count >= 1 and merged:
                                # Strict mode: for post links return only extractor-derived media.
                                # This prevents unrelated HTML assets from being delivered.
                                return [str(p) for p in merged], info

                            # Retry with metadata-only extraction to recover full carousel URLs
                            # when direct download extraction materializes an incomplete subset.
                            meta_info = self._extract_instagram_post_info_no_download(url)
                            if meta_info:
                                meta_assets = self._download_direct_media_assets(meta_info, download_dir)
                                if meta_assets:
                                    return [str(p) for p in meta_assets], info
                            sidecar_assets = self._fallback_instagram_sidecar_assets(url, download_dir)
                            if sidecar_assets:
                                return [str(p) for p in sidecar_assets], info

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
                    if "no video formats found" in err:
                        logger.warning("No video formats found, trying fallback chain")
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

            if not is_instagram_post:
                html_assets = self._fallback_instagram_html_assets(
                    url,
                    download_dir,
                    prefer_video=is_instagram_video_link,
                )
                if html_assets:
                    return [str(p) for p in html_assets], {"title": "Instagram media", "duration": None}

                gallery_assets = self._fallback_instagram_gallery_assets(url, download_dir)
                if gallery_assets and not is_instagram_video_link:
                    return [str(p) for p in gallery_assets], {"title": "Instagram media", "duration": None}

            if is_instagram_post and option != "mp3":
                meta_info = self._extract_instagram_post_info_no_download(url)
                if meta_info:
                    meta_assets = self._download_direct_media_assets(meta_info, download_dir)
                    if meta_assets:
                        return [str(p) for p in meta_assets], {
                            "title": meta_info.get("title") or "Instagram media",
                            "duration": meta_info.get("duration"),
                        }
                structured_assets = self._fallback_instagram_post_structured_assets(url, download_dir)
                if structured_assets:
                    return [str(p) for p in structured_assets], {
                        "title": "Instagram media",
                        "duration": None,
                    }
                sidecar_assets = self._fallback_instagram_sidecar_assets(url, download_dir)
                if sidecar_assets:
                    return [str(p) for p in sidecar_assets], {
                        "title": "Instagram media",
                        "duration": None,
                    }
                # Final no-error fallback for post links: send at least the canonical cover image.
                fallback_asset = self._fallback_instagram_og_asset(
                    url,
                    download_dir,
                    allow_image=True,
                )
                if not fallback_asset:
                    fallback_asset = self._fallback_instagram_oembed_asset(url, download_dir)
                if fallback_asset:
                    return [str(fallback_asset)], {"title": "Instagram media", "duration": None}

            fallback_asset = self._fallback_instagram_og_asset(
                url,
                download_dir,
                allow_image=(not is_instagram_video_link) and (not is_instagram_post),
            )
            if not fallback_asset and (not is_instagram_video_link) and (not is_instagram_post):
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
        video_ext = {".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi"}
        primary = next((p for p in resolved_paths if p.suffix.lower() in video_ext), resolved_paths[0])
        return DownloadResult(
            file_paths=resolved_paths,
            title=info.get("title") or "Untitled",
            duration_sec=duration_int,
            option=option,
            media_kind=self._classify_media(primary, option),
        )
