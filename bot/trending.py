import requests
from bs4 import BeautifulSoup

URL = "https://www.billboard.com/charts/hot-100/"


def get_trending(limit: int = 10):
    r = requests.get(URL, timeout=10)
    r.raise_for_status()

    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    for tag in soup.select("li ul li h3"):
        title = tag.get_text(strip=True)
        if title:
            items.append(title)
        if len(items) >= limit:
            break

    return items
