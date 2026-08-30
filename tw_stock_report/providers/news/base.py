"""新聞 provider 共用介面。

每個 provider 是一個 `fetch(keywords, limit) -> ProviderResult[list[NewsItem]]` 函式，
絕不對外拋出例外；單一來源失敗只影響自己的結果，由 aggregator 統籌其餘來源。
"""
from __future__ import annotations

from typing import Callable, Protocol

from ...models import NewsItem, ProviderResult


class NewsFetchFn(Protocol):
    def __call__(self, keywords: list[str], limit: int) -> ProviderResult[list[NewsItem]]: ...
