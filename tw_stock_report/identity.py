"""股票代號／名稱 -> StockIdentity 正規化。

這是唯一允許在查無此股票時往外拋例外（IdentityNotFound）的模組：
沒有身分就沒有辦法產出任何報告內容，其餘所有 provider 都必須吸收自己的錯誤。
"""
from __future__ import annotations

from . import aliases_seed, cache, config
from .finmind_client import FinMindError, fetch_dataset
from .models import StockIdentity

_MARKET_TYPE_MAP = {
    "twse": "上市",
    "tpex": "上櫃",
    "otc": "上櫃",
}


class IdentityNotFound(Exception):
    pass


def _load_stock_info_table() -> list[dict]:
    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockInfo")

    try:
        return cache.cached_call(
            "TaiwanStockInfo", config.CACHE_TTL_STOCK_INFO, _fetch
        )
    except FinMindError as exc:
        raise IdentityNotFound(
            f"無法取得股票基本資料清單（FinMind TaiwanStockInfo 失敗）：{exc}"
        ) from exc


def resolve(user_input: str) -> StockIdentity:
    user_input = (user_input or "").strip()
    if not user_input:
        raise IdentityNotFound("請輸入股票代號或名稱")

    table = _load_stock_info_table()
    if not table:
        raise IdentityNotFound("股票基本資料清單為空，無法比對")

    is_numeric = user_input.isdigit()
    match: dict | None = None

    if is_numeric:
        # 同一代號可能因上市/上櫃切換出現多筆，取最新一筆（表格通常已按時間排序，保守起見取最後一筆）
        candidates = [row for row in table if row.get("stock_id") == user_input]
        if candidates:
            match = candidates[-1]
    else:
        # 先精確比對公司名稱，再退而比對「名稱包含輸入字串」
        exact = [row for row in table if row.get("stock_name") == user_input]
        if exact:
            match = exact[-1]
        else:
            partial = [
                row
                for row in table
                if user_input in (row.get("stock_name") or "")
            ]
            if partial:
                match = partial[-1]

    if match is None:
        raise IdentityNotFound(f"查無股票「{user_input}」，請確認代號或名稱是否正確")

    stock_id = match.get("stock_id", "")
    company_name = match.get("stock_name", "")
    industry_name = match.get("industry_category", "") or "未知產業"
    market_type = _MARKET_TYPE_MAP.get((match.get("type") or "").lower(), "未知")

    aliases = aliases_seed.get_aliases(stock_id)

    return StockIdentity(
        stock_id=stock_id,
        company_name=company_name,
        aliases=aliases,
        industry_name=industry_name,
        market_type=market_type,
    )
