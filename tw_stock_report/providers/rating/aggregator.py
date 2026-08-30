"""目標價／評等聚合器：重用新聞 provider 基礎設施，套用評等關鍵字組後做規則式抽取。

不假設任何官方目標價/評等 API；完全從公開新聞標題與摘要中規則式整理，
查無結果時交由呼叫端顯示規格要求的固定文字，不視為錯誤。
"""
from __future__ import annotations

import concurrent.futures
from datetime import date

from ... import config
from ...models import RatingItem, StockIdentity
from ..news import cnyes
from . import extractor

_RATING_KEYWORD_SUFFIXES = ["目標價", "評等", "法人", "買進", "中立", "賣出", "外資 看法"]
_RATING_SEARCH_LIMIT = 20


def _build_rating_keywords(identity: StockIdentity) -> list[str]:
    # 公司名稱單獨查詢的召回範圍最廣，排在最前面，其餘為規格要求的複合關鍵字組
    return [identity.company_name] + [f"{identity.company_name} {suffix}" for suffix in _RATING_KEYWORD_SUFFIXES]


def gather_ratings(identity: StockIdentity) -> tuple[list[RatingItem], list[str]]:
    keywords = _build_rating_keywords(identity)
    errors: list[str] = []
    ratings: list[RatingItem] = []
    seen_urls: set[str] = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(keywords)) as pool:
        futures = {pool.submit(cnyes.fetch_by_keyword, kw, _RATING_SEARCH_LIMIT): kw for kw in keywords}
        for future in concurrent.futures.as_completed(futures):
            keyword = futures[future]
            result = future.result()
            if not result.ok:
                errors.append(f"鉅亨網（評等關鍵字：{keyword}）：{result.error}")
                continue
            for item in result.data:
                if item.url in seen_urls:
                    continue
                haystack = f"{item.title} {item.snippet}"
                if identity.company_name not in haystack and identity.stock_id not in haystack:
                    continue  # 標題與摘要都未提及本股票，關鍵字命中但相關性不足，排除以降低雜訊
                rating = extractor.extract_rating(item)
                if rating is not None:
                    seen_urls.add(item.url)
                    ratings.append(rating)

    ratings.sort(key=lambda r: r.publish_date or date.min, reverse=True)
    return ratings, errors
