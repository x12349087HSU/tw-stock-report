"""新聞聚合器：多來源、多關鍵字、三層 fallback，單一來源失敗互不影響。

三層 fallback：
  1. FinMind 個股新聞 feed（依 stock_id 直接查詢，最精準）
  2. 鉅亨網關鍵字搜尋，依序嘗試 company_name / company_name+id / id+company_name /
     industry+company_name 這四組個股相關關鍵字
  3. 若以上兩層加總仍不足 NEWS_MIN_ITEMS_BEFORE_INDUSTRY_FALLBACK 篇，
     改用「產業名稱」關鍵字查近 30 天新聞作為產業趨勢的 fallback 素材
"""
from __future__ import annotations

import concurrent.futures
import logging
from datetime import date

from ... import config
from ...models import NewsItem, StockIdentity
from . import cnyes, finmind_news

logger = logging.getLogger("tw_stock_report.news")


def _dedupe(items: list[NewsItem]) -> list[NewsItem]:
    seen: set[str] = set()
    out: list[NewsItem] = []
    for item in items:
        if item.url not in seen:
            seen.add(item.url)
            out.append(item)
    return out


def _build_keyword_tiers(identity: StockIdentity) -> list[str]:
    name = identity.company_name
    return [
        name,
        f"{name} {identity.stock_id}",
        f"{identity.stock_id} {name}",
        f"{identity.industry_name} {name}",
    ]


def gather_stock_news(identity: StockIdentity) -> tuple[list[NewsItem], list[str]]:
    """回傳 (個股新聞清單, 各來源錯誤訊息清單)。任何來源失敗都只記錄訊息，不會中止彙整。"""
    errors: list[str] = []
    collected: list[NewsItem] = []

    keyword_tiers = _build_keyword_tiers(identity)

    def _call_finmind():
        return finmind_news.fetch_stock_news(identity.stock_id, days_back=60, limit=config.NEWS_MAX_ITEMS_PER_PROVIDER)

    def _call_cnyes_tier(keyword: str):
        return cnyes.fetch_by_keyword(keyword, limit=config.NEWS_MAX_ITEMS_PER_PROVIDER)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        finmind_future = pool.submit(_call_finmind)
        cnyes_futures = {pool.submit(_call_cnyes_tier, kw): kw for kw in keyword_tiers}

        result = finmind_future.result()
        if result.ok:
            collected.extend(result.data)
        else:
            errors.append(f"FinMind 個股新聞：{result.error}")

        for future in concurrent.futures.as_completed(cnyes_futures):
            keyword = cnyes_futures[future]
            result = future.result()
            if result.ok:
                collected.extend(result.data)
            else:
                errors.append(f"鉅亨網（關鍵字：{keyword}）：{result.error}")

    return _dedupe(collected), errors


def gather_industry_news(identity: StockIdentity) -> tuple[list[NewsItem], list[str]]:
    """第三層 fallback：以產業名稱查近期新聞。"""
    result = cnyes.fetch_by_keyword(identity.industry_name, limit=config.NEWS_MAX_ITEMS_PER_PROVIDER)
    if result.ok:
        return result.data, []
    return [], [f"鉅亨網（產業關鍵字：{identity.industry_name}）：{result.error}"]


def gather_all_news(identity: StockIdentity) -> tuple[list[NewsItem], list[NewsItem], list[str]]:
    """完整彙整流程，回傳 (個股新聞, 產業 fallback 新聞, 所有錯誤訊息)。"""
    stock_news, errors = gather_stock_news(identity)
    stock_news.sort(key=lambda i: i.publish_date or date.min, reverse=True)

    industry_news: list[NewsItem] = []
    if len(stock_news) < config.NEWS_MIN_ITEMS_BEFORE_INDUSTRY_FALLBACK:
        industry_news, industry_errors = gather_industry_news(identity)
        errors.extend(industry_errors)
        industry_news = [n for n in industry_news if n.url not in {s.url for s in stock_news}]

    return stock_news, industry_news, errors
