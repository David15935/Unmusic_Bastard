import requests
from bs4 import BeautifulSoup

DEEZEER_CHART_URL = "https://api.deezer.com/chart/0/tracks"
BILLBOARD_URL = "https://www.billboard.com/charts/hot-100/"


def _deezer_trending(limit: int):
    r = requests.get(DEEZEER_CHART_URL, params={"limit": limit}, timeout=10)
    r.raise_for_status()
    data = r.json().get("data", [])

    items = []
    for track in data:
        title = track.get("title")
        artist = (track.get("artist") or {}).get("name")
        if title and artist:
            items.append(f"{artist} - {title}")
        if len(items) >= limit:
            break
    return items


def _billboard_trending(limit: int):
    r = requests.get(BILLBOARD_URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    titles = [t.get_text(strip=True) for t in soup.select("li ul li h3") if t.get_text(strip=True)]
    artists = [
        a.get_text(strip=True)
        for a in soup.select("li ul li span.c-label")
        if a.get_text(strip=True) and a.get_text(strip=True).lower() not in {"new", "-", "re-entry"}
    ]

    items = []
    for idx, title in enumerate(titles[:limit]):
        artist = artists[idx] if idx < len(artists) else "Unknown Artist"
        items.append(f"{artist} - {title}")
    return items


def get_trending(limit: int = 10):
    try:
        items = _deezer_trending(limit)
        if items:
            return items
    except Exception:
        pass

    items = _billboard_trending(limit)
    return items[:limit]
