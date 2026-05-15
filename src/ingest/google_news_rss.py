import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class NewsItem:
    title: str
    url: str
    published: str
    source: str
    snippet: str
    category_id: int
    keyword: str
    fetched_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "url": self.url,
            "published": self.published,
            "source": self.source,
            "snippet": self.snippet,
            "category_id": self.category_id,
            "keyword": self.keyword,
            "fetched_at": self.fetched_at,
        }


def build_gdelt_url(keyword: str, max_records: int = 50) -> str:
    q = urllib.parse.quote_plus(keyword)
    return (
        f"https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={q}&mode=artlist&maxrecords={max_records}&format=json"
    )


def fetch_rss(url: str) -> list[dict[str, str]]:
    import feedparser

    feed = feedparser.parse(url)
    items: list[dict[str, str]] = []
    for entry in feed.entries:
        items.append(
            {
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published": entry.get("published") or entry.get("updated") or "",
                "source": (
                    entry.get("source", {}).get("title", "")
                    if isinstance(entry.get("source"), dict)
                    else entry.get("source", "")
                ),
                "snippet": entry.get("summary", ""),
            }
        )
    return items


def fetch_by_keyword(keyword: str, category_id: int) -> list[NewsItem]:
    import requests

    url = build_gdelt_url(keyword)
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    data = resp.json()

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return [
        NewsItem(
            title=art.get("title", "") or "",
            url=art.get("url", "") or "",
            published=art.get("seendate", "") or "",
            source=art.get("domain", "") or "",
            snippet=art.get("socialimage", "") or art.get("title", ""),
            category_id=category_id,
            keyword=keyword,
            fetched_at=fetched_at,
        )
        for art in data.get("articles", [])
    ]
