import asyncio
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Optional
import shutil
import glob
import subprocess
import logging

import yt_dlp

BASE_DIR = Path(__file__).resolve().parent.parent
DOWNLOADS_DIR = BASE_DIR / "downloads"
COVERS_DIR = BASE_DIR / "covers"
CACHE_DIR = BASE_DIR / ".cache"
CACHE_FILE = CACHE_DIR / "index.json"

logger = logging.getLogger(__name__)

MAX_BYTES = 50 * 1024 * 1024
DEFAULT_SPLIT_SECONDS = 10 * 60

CACHE_LOCK = asyncio.Lock()
_CACHE: Dict[str, Dict] = {}
_JS_WARNING_SHOWN = False


class _YDLLogger:
    def debug(self, msg):
        logger.debug(msg)

    def info(self, msg):
        logger.info(msg)

    def warning(self, msg):
        global _JS_WARNING_SHOWN
        text = str(msg)
        if "No supported JavaScript runtime could be found" in text:
            if not _JS_WARNING_SHOWN:
                _JS_WARNING_SHOWN = True
                logger.warning(
                    "JS runtime missing for yt-dlp. Install Node.js for best YouTube extraction quality."
                )
            return
        logger.warning(text)

    def error(self, msg):
        logger.error(msg)


def _progress(d):
    if d.get('status') == 'downloading':
        logger.info("yt-dlp downloading: %s %s", d.get('filename'), d.get('eta'))
    elif d.get('status') == 'finished':
        logger.info("yt-dlp finished: %s", d.get('filename'))


def _get_js_runtimes() -> Dict[str, Dict[str, str]]:
    runtimes: Dict[str, Dict[str, str]] = {}
    for runtime in ("node", "deno", "bun"):
        found = shutil.which(runtime)
        if found:
            runtimes[runtime] = {"path": found}
    return runtimes

def _ensure_dirs():
    DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
    COVERS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _hash_key(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def _is_url(text: str) -> bool:
    return text.startswith("http://") or text.startswith("https://")


def _load_cache_from_disk() -> Dict[str, Dict]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache_to_disk(cache: Dict[str, Dict]) -> None:
    CACHE_FILE.write_text(json.dumps(cache, ensure_ascii=True, indent=2), encoding="utf-8")


async def _get_cache() -> Dict[str, Dict]:
    global _CACHE
    if _CACHE:
        return _CACHE
    async with CACHE_LOCK:
        if not _CACHE:
            _CACHE = _load_cache_from_disk()
        return _CACHE


async def _set_cache(key: str, value: Dict) -> None:
    global _CACHE
    async with CACHE_LOCK:
        if not _CACHE:
            _CACHE = _load_cache_from_disk()
        _CACHE[key] = value
        _save_cache_to_disk(_CACHE)


async def _run_yt_dlp(ydl_opts: Dict, url: str):
    def _task():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=True)

    return await asyncio.to_thread(_task)



def _find_ffmpeg_location() -> Optional[str]:
    env_path = os.getenv("FFMPEG_LOCATION") or os.getenv("FFMPEG_PATH")
    if env_path and os.path.exists(env_path):
        return env_path

    found = shutil.which("ffmpeg")
    if found:
        return str(Path(found).parent)

    local = os.getenv("LOCALAPPDATA")
    if local:
        winget_root = Path(local) / "Microsoft" / "WinGet" / "Packages"
        if winget_root.exists():
            matches = winget_root.glob("Gyan.FFmpeg*_*/ffmpeg-*/bin")
            for m in matches:
                if (m / "ffmpeg.exe").exists():
                    return str(m)

    return None


async def search_youtube(query: str, limit: int = 10) -> List[Dict]:
    _ensure_dirs()
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
        "noplaylist": True,
    }

    def _task():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch{limit}:{query}", download=False)
            return info.get("entries", [])

    entries = await asyncio.to_thread(_task)
    results = []
    for e in entries:
        if not e:
            continue
        results.append(
            {
                "id": e.get("id"),
                "title": e.get("title"),
                "uploader": e.get("uploader"),
                "duration": e.get("duration"),
                "url": e.get("url") or e.get("webpage_url"),
                "webpage_url": e.get("webpage_url"),
                "thumbnail": e.get("thumbnail"),
            }
        )
    return results


async def get_info(query_or_url: str) -> Optional[str]:
    if not query_or_url:
        return None

    if _is_url(query_or_url):
        ydl_opts = {"quiet": True, "no_warnings": True, "skip_download": True}

        def _task():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(query_or_url, download=False)

        info = await asyncio.to_thread(_task)
    else:
        results = await search_youtube(query_or_url, limit=1)
        if not results:
            return None
        info = results[0]

    title = info.get("title", "Unknown")
    uploader = info.get("uploader") or info.get("channel") or "Unknown"
    duration = info.get("duration")
    url = info.get("webpage_url") or info.get("url") or query_or_url

    return f"{title} | {uploader} | {duration or 'Unknown'}s | {url}"


async def fetch_audio(query_or_url: str) -> Dict:
    _ensure_dirs()

    url = query_or_url
    info_for_cache = None

    if not _is_url(query_or_url):
        results = await search_youtube(query_or_url, limit=1)
        if not results:
            raise RuntimeError("No results found.")
        info_for_cache = results[0]
        url = info_for_cache.get("webpage_url") or info_for_cache.get("url")

    cache_key = _hash_key(url)
    cache = await _get_cache()
    cached = cache.get(cache_key)
    if cached:
        cached_path = cached.get("path")
        if cached_path and os.path.exists(cached_path):
            return cached

    ffmpeg_location = _find_ffmpeg_location()
    ydl_opts = {
        "format": "bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio",
        "outtmpl": {
            "default": str(DOWNLOADS_DIR / "%(id)s.%(ext)s"),
            "thumbnail": str(COVERS_DIR / "%(id)s.%(ext)s"),
        },
        "writethumbnail": False,
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "cachedir": str(CACHE_DIR / "yt-dlp"),
        "concurrent_fragment_downloads": 4,
        "retries": 3,
        "logger": _YDLLogger(),
        "progress_hooks": [_progress],
    }
    js_runtimes = _get_js_runtimes()
    if js_runtimes:
        ydl_opts["js_runtimes"] = js_runtimes
    if ffmpeg_location:
        ydl_opts["ffmpeg_location"] = ffmpeg_location

    info = await _run_yt_dlp(ydl_opts, url)
    video_id = info.get("id")
    title = info.get("title")
    uploader = info.get("uploader") or info.get("channel")
    duration = info.get("duration")
    webpage_url = info.get("webpage_url") or url

    mp3_path = str(DOWNLOADS_DIR / f"{video_id}.mp3")

    if not os.path.exists(mp3_path):
        candidates = glob.glob(str(DOWNLOADS_DIR / f"{video_id}.*"))
        raw = None
        if candidates:
            priority = [".m4a", ".webm", ".opus", ".ogg", ".aac"]
            candidates.sort(
                key=lambda p: priority.index(Path(p).suffix)
                if Path(p).suffix in priority
                else 99
            )
            raw = candidates[0]

        if not raw:
            candidate = yt_dlp.YoutubeDL({"quiet": True}).prepare_filename(info)
            if os.path.exists(candidate):
                raw = candidate

        if raw:
            ffmpeg_bin = (
                str(Path(ffmpeg_location) / "ffmpeg.exe") if ffmpeg_location else "ffmpeg"
            )

            logger.info("Converting to mp3 raw=%s mp3=%s", raw, mp3_path)
            def _convert():
                subprocess.run(
                    [
                        ffmpeg_bin,
                        "-y",
                        "-i",
                        raw,
                        "-vn",
                        "-ab",
                        "192k",
                        mp3_path,
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )

            await asyncio.to_thread(_convert)

            for f in glob.glob(str(DOWNLOADS_DIR / f"{video_id}.*")):
                if not f.lower().endswith(".mp3"):
                    try:
                        os.remove(f)
                    except Exception:
                        pass

    for _ in range(10):
        if os.path.exists(mp3_path):
            break
        await asyncio.sleep(0.3)

    if not os.path.exists(mp3_path):
        raise RuntimeError("MP3 conversion failed.")

    size = os.path.getsize(mp3_path)
    logger.info("MP3 ready path=%s size=%s", mp3_path, size)

    payload = {
        "id": video_id,
        "title": title,
        "uploader": uploader,
        "duration": duration,
        "url": webpage_url,
        "path": mp3_path,
        "cached_at": int(time.time()),
    }

    await _set_cache(cache_key, payload)
    return payload


async def split_audio_for_telegram(
    source_path: str,
    max_bytes: int = MAX_BYTES,
    split_seconds: int = DEFAULT_SPLIT_SECONDS,
) -> List[str]:
    if not os.path.exists(source_path):
        raise RuntimeError(f"Audio file not found: {source_path}")

    if os.path.getsize(source_path) <= max_bytes:
        return [source_path]

    ffmpeg_location = _find_ffmpeg_location()
    ffmpeg_bin = str(Path(ffmpeg_location) / "ffmpeg.exe") if ffmpeg_location else "ffmpeg"
    source = Path(source_path)
    out_pattern = source.with_name(f"{source.stem}_part%03d{source.suffix}")

    logger.info("Splitting large file path=%s", source_path)

    def _split() -> None:
        subprocess.run(
            [
                ffmpeg_bin,
                "-y",
                "-i",
                str(source),
                "-f",
                "segment",
                "-segment_time",
                str(split_seconds),
                "-c",
                "copy",
                str(out_pattern),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )

    await asyncio.to_thread(_split)

    parts = sorted(str(p) for p in source.parent.glob(f"{source.stem}_part*{source.suffix}"))
    if not parts:
        raise RuntimeError("Could not split large audio file.")

    safe_parts = [p for p in parts if os.path.getsize(p) <= max_bytes]
    if not safe_parts:
        raise RuntimeError("Split parts are still above Telegram limit.")

    logger.info("Split complete parts=%s", len(safe_parts))
    return safe_parts

