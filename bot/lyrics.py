import os
import requests
import lyricsgenius
from dotenv import load_dotenv

load_dotenv()
GENIUS_TOKEN = os.getenv("GENIUS_TOKEN")

_genius = None


def _get_client():
    global _genius
    if _genius is None:
        if not GENIUS_TOKEN:
            return None
        _genius = lyricsgenius.Genius(
            GENIUS_TOKEN,
            timeout=10,
            retries=1,
            skip_non_songs=True,
            remove_section_headers=True,
        )
    return _genius


def _fetch_lyrics_lrclib(query: str) -> str | None:
    try:
        r = requests.get("https://lrclib.net/api/search", params={"q": query}, timeout=10)
        r.raise_for_status()
        data = r.json()
        if not data:
            return None
        candidate = data[0]
        return candidate.get("plainLyrics") or candidate.get("syncedLyrics")
    except Exception:
        return None


def fetch_lyrics(query: str) -> str:
    query = query.strip()
    if not query:
        return "Usage: /lyrics <song name>"

    client = _get_client()
    if client:
        try:
            song = client.search_song(query)
            if song and song.lyrics:
                return song.lyrics
        except Exception:
            pass

    fallback = _fetch_lyrics_lrclib(query)
    if fallback:
        return fallback

    if not GENIUS_TOKEN:
        return "Lyrics not found. Add GENIUS_TOKEN in .env for better results."
    return "Lyrics not found."
