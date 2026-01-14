# bot/music_api.py
import aiohttp
import yt_dlp
import asyncio

# -----------------------------
# Search for a song (stub)
# -----------------------------
async def search_song(query: str):
    """
    Search for a song by name.
    Returns a list of dictionaries with song info.
    """
    # TODO: implement real search (e.g., YouTube API, Spotify API)
    return [
        {
            "title": f"Sample Song for '{query}'",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "duration": "3:33",
            "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
        }
    ]

# -----------------------------
# Download a song
# -----------------------------
async def download_song(url: str, output_path: str = "./downloads"):
    """
    Download a song from a URL (YouTube for now) using yt-dlp.
    Returns local file path.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f"{output_path}/%(title)s.%(ext)s",
        'quiet': True,
        'nocheckcertificate': True,
        'noplaylist': True,
        'ignoreerrors': True,
    }

    loop = asyncio.get_event_loop()
    def run_ydl():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    file_path = await loop.run_in_executor(None, run_ydl)
    return file_path

# -----------------------------
# Get lyrics (stub)
# -----------------------------
async def get_lyrics(song_name: str):
    """
    Return lyrics for a song.
    """
    # TODO: Integrate Genius API or any lyrics source
    return f"Lyrics for '{song_name}' are not implemented yet."

# -----------------------------
# Get song info (stub)
# -----------------------------
async def get_info(url: str):
    """
    Return song info (title, duration, thumbnail) from a URL.
    """
    # TODO: Parse real info using yt-dlp or API
    return {
        "title": "Sample Song",
        "url": url,
        "duration": "3:33",
        "thumbnail": "https://img.youtube.com/vi/dQw4w9WgXcQ/maxresdefault.jpg"
    }
