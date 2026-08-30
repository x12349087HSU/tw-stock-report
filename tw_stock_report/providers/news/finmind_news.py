"""FinMind TaiwanStockNews：已按 stock_id 預先聚合多家新聞來源的個股新聞 feed。

這是 FinMind 官方 API 的一部分（非直接對原始新聞網站發送請求），因此不受個別新聞網站
robots.txt／著作權聲明規範；但仍遵守 FinMind 自身的請求頻率與快取原則。
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from ... import cache, config
from ...finmind_client import FinMindError, fetch_dataset
from ...models import NewsItem, ProviderResult
from ..base import safe_provider


def _parse_item(row: dict, matched_keyword: str) -> NewsItem | None:
    try:
        dt = datetime.fromisoformat(row["date"])
    except (KeyError, ValueError):
        dt = None
    title = (row.get("title") or "").strip()
    url = (row.get("link") or "").strip()
    if not title or not url:
        return None
    return NewsItem(
        title=title,
        publish_date=dt.date() if dt else None,
        source=row.get("source", "") or "FinMind聚合新聞",
        url=url,
        snippet="",
        matched_keyword=matched_keyword,
    )


@safe_provider("FinMind 個股新聞")
def fetch_stock_news(stock_id: str, days_back: int, limit: int) -> list[NewsItem]:
    start_date = (date.today() - timedelta(days=days_back)).isoformat()

    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockNews", data_id=stock_id, start_date=start_date)

    key = f"news_finmind:{stock_id}:{start_date}"
    raw = cache.cached_call(key, config.CACHE_TTL_NEWS, _fetch)

    seen_urls: set[str] = set()
    items: list[NewsItem] = []
    for row in raw:
        item = _parse_item(row, matched_keyword=f"stock_id:{stock_id}")
        if item and item.url not in seen_urls:
            seen_urls.add(item.url)
            items.append(item)
    if not items:
        raise FinMindError("FinMind 個股新聞查無資料")
    items.sort(key=lambda i: i.publish_date or date.min, reverse=True)
    return items[:limit]
