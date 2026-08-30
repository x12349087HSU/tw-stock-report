"""鉅亨網（news.cnyes.com）新聞搜尋 provider。

使用鉅亨網公開的新聞搜尋 API（非受限路徑，robots.txt 未限制一般或 AI 爬蟲存取）。
"""
from __future__ import annotations

import re
from datetime import date, datetime

from ... import cache, config, http_client
from ...models import NewsItem, ProviderResult
from ..base import safe_provider

_SEARCH_URL = "https://api.cnyes.com/media/api/v1/search/news"
_TAG_RE = re.compile(r"<[^>]+>")


def _strip_tags(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _parse_item(row: dict, matched_keyword: str) -> NewsItem | None:
    title = _strip_tags(row.get("title", ""))
    news_id = row.get("newsId")
    if not title or not news_id:
        return None
    ts = row.get("publishAt")
    publish_date = None
    if ts:
        try:
            publish_date = datetime.fromtimestamp(int(ts)).date()
        except (ValueError, OSError):
            publish_date = None
    return NewsItem(
        title=title,
        publish_date=publish_date,
        source=row.get("signature", "") or "鉅亨網",
        url=f"https://news.cnyes.com/news/id/{news_id}",
        snippet=_strip_tags(row.get("content", "")),
        matched_keyword=matched_keyword,
    )


@safe_provider("鉅亨網")
def fetch_by_keyword(keyword: str, limit: int) -> list[NewsItem]:
    def _fetch() -> dict:
        resp = http_client.get(_SEARCH_URL, params={"q": keyword, "limit": limit})
        return resp.json()

    key = f"news_cnyes:{keyword}:{limit}"
    payload = cache.cached_call(key, config.CACHE_TTL_NEWS, _fetch)

    rows = (payload or {}).get("items", {}).get("data", [])
    items: list[NewsItem] = []
    seen_urls: set[str] = set()
    for row in rows:
        item = _parse_item(row, matched_keyword=keyword)
        if item and item.url not in seen_urls:
            seen_urls.add(item.url)
            items.append(item)
    if not items:
        raise RuntimeError(f"鉅亨網關鍵字「{keyword}」查無新聞")
    return items[:limit]
