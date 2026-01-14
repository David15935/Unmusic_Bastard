# bot/music_api.py
import asyncio
from pathlib import Path
import yt_dlp
from aiohttp import ClientSession

DOWNLOAD_DIR = Path("./downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)

YTDL_OPTS_INFO = {"format": "bestaudio/best", "quiet": True, "noplaylist": True}
YTDL_OPTS_DOWNLOAD = {
    "format": "bestaudio/best",
    "outtmpl": str(DOWNLOAD_DIR / "%(id)s.%(ext)s"),
    "quiet": True,
    "noplaylist": True,
    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
}


async def _run_blocking(func, *args, **kwargs):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: func(*args, **kwargs))


async def search_youtube(query: str, limit: int = 5, offset: int = 0):
    """
    Return list of dicts: {id, title, webpage_url, duration, thumbnail}
    Supports simple pagination via offset
    """
    def _search():
        with yt_dlp.YoutubeDL(YTDL_OPTS_INFO) as ydl:
            results = ydl.extract_info(f"ytsearch{limit+offset}:{query}", download=False)
            entries = results.get("entries", []) if results else []
            # slice offset..offset+limit
            entries = entries[offset: offset + limit]
            out = []
            for e in entries:
                out.append({
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "webpage_url": e.get("webpage_url"),
                    "duration": e.get("duration"),
                    "thumbnail": e.get("thumbnail"),
                })
            return out
    return await _run_blocking(_search)


async def get_info(video_url: str):
    """Return metadata dict for URL"""
    def _info():
        with yt_dlp.YoutubeDL(YTDL_OPTS_INFO) as ydl:
            info = ydl.extract_info(video_url, download=False)
            return {
                "id": info.get("id"),
                "title": info.get("title"),
                "webpage_url": info.get("webpage_url"),
                "duration": info.get("duration"),
                "thumbnail": info.get("thumbnail"),
            }
    return await _run_blocking(_info)


async def download_audio(video_url: str):
    """
    Download audio, convert to mp3, return local file path string.
    Caches by YouTube video id: if file exists, returns path immediately.
    """
    # get id first
    info = await get_info(video_url)
    vid = info.get("id")
    if not vid:
        raise RuntimeError("Failed to get video id")

    # expected mp3 path:
    mp3_path = DOWNLOAD_DIR / f"{vid}.mp3"
    if mp3_path.exists():
        return str(mp3_path)

    def _download():
        with yt_dlp.YoutubeDL(YTDL_OPTS_DOWNLOAD) as ydl:
            # ydl will write file to DOWNLOAD_DIR/<id>.<ext> then postprocess to mp3
            ydl.download([video_url])
            # find the mp3 file (yt-dlp outtmpl produces id.ext, then ffmpeg produces id.mp3)
            return str(mp3_path)

    return await _run_blocking(_download)


async def get_trending(limit: int = 10):
    """
    Try to extract trends from YouTube Trending page (yt-dlp can read it)
    """
    def _trending():
        url = "https://www.youtube.com/feed/trending"
        with yt_dlp.YoutubeDL(YTDL_OPTS_INFO) as ydl:
            info = ydl.extract_info(url, download=False)
            entries = info.get("entries", []) if info else []
            out = []
            for e in entries[:limit]:
                out.append({
                    "id": e.get("id"),
                    "title": e.get("title"),
                    "webpage_url": e.get("webpage_url"),
                    "duration": e.get("duration"),
                    "thumbnail": e.get("thumbnail"),
                })
            return out
    try:
        return await _run_blocking(_trending)
    except Exception:
        return []


async def get_lyrics_basic(query: str):
    """
    Try lyrics.ovh first. query may be "artist - title" or "title".
    This is a fallback; for better results integrate Genius scraping later.
    """
    # attempt parse artist/title naive split
    parts = query.split(" - ", 1)
    if len(parts) == 2:
        artist, title = parts[0].strip(), parts[1].strip()
    else:
        # try lyrics.ovh with unknown artist returns 404 often; we'll try just title
        artist, title = "", query.strip()

    if artist:
        url = f"https://api.lyrics.ovh/v1/{artist}/{title}"
        async with ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("lyrics", "No lyrics found")
    # fallback: try search lyric.ovh by title alone won't work reliably; return not found
    return "Lyrics not found via basic API. For better lyrics integrate Genius API (requires scraping the page)."
