import os
from dotenv import load_dotenv
import lyricsgenius

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


def fetch_lyrics(query: str) -> str:
    client = _get_client()
    if not client:
        return "GENIUS_TOKEN is not configured."

    try:
        song = client.search_song(query)
        if not song or not song.lyrics:
            return "Lyrics not found."
        return song.lyrics
    except Exception:
        return "Lyrics not found."
