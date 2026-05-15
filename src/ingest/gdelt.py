import urllib.request
import json
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


def fetch_gdelt(keyword: str, category_id: int, max_records: int = 50) -> list[NewsItem]:
    import ssl

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    query = urllib.parse.quote_plus(keyword)
    url = (
        f"https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={query}&mode=artlist&maxrecords={max_records}&format=json"
    )

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    with urllib.request.urlopen(url, timeout=20, context=ctx) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    items: list[NewsItem] = []
    for art in data.get("articles", []):
        items.append(
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
        )
    return items
