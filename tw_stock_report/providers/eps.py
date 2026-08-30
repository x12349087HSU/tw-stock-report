"""EPS provider：FinMind 財報(EPS 科目) 主要 + 公開資訊觀測站(MOPS) 官方備援。

FinMind 的 TaiwanStockFinancialStatements/EPS 科目本身就是「單季」數字。
MOPS 合併綜合損益表則是「累計」數字（第2季=上半年累計、第3季=前三季累計、第4季=全年累計），
官方備援因此需要用累計值相減換算成單季 EPS。
"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from .. import cache, config, http_client
from ..finmind_client import FinMindError, fetch_dataset
from ..models import EpsRow, ProviderResult, StockIdentity
from .base import safe_provider

_MARKET_TO_TYPEK = {"上市": "sii", "上櫃": "otc"}


def _quarter_of(month: int) -> int:
    return (month - 1) // 3 + 1


@safe_provider("FinMind")
def _fetch_finmind(stock_id: str, start_date: str) -> list[EpsRow]:
    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockFinancialStatements", data_id=stock_id, start_date=start_date)

    key = f"eps:{stock_id}:{start_date}"
    raw = cache.cached_call(key, config.CACHE_TTL_EPS, _fetch)

    rows: list[EpsRow] = []
    for item in raw:
        if item.get("type") != "EPS":
            continue
        try:
            d = date.fromisoformat(item["date"])
            rows.append(EpsRow(year=d.year, quarter=_quarter_of(d.month), eps=float(item["value"])))
        except (KeyError, ValueError, TypeError):
            continue
    if not rows:
        raise FinMindError("FinMind 回傳 EPS 資料為空")
    rows.sort(key=lambda r: (r.year, r.quarter))
    return rows


def _mops_income_statement_url(stock_id: str, typek: str, roc_year: int, season: int) -> str:
    return (
        "https://mopsov.twse.com.tw/mops/web/ajax_t164sb04"
        f"?encodeURIComponent=1&step=1&firstin=1&off=1&keyword4=&code1=&TYPEK2="
        f"&checkbtn=&queryName=co_id&inpuType=co_id&TYPEK={typek}&isnew=false"
        f"&co_id={stock_id}&year={roc_year}&season={season:02d}"
    )


def _fetch_mops_cumulative_eps(stock_id: str, typek: str, roc_year: int, season: int) -> float | None:
    url = _mops_income_statement_url(stock_id, typek, roc_year, season)
    resp = http_client.get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    for tr in soup.select("table.hasBorder tr"):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        label = cells[0].get_text(strip=True)
        if label == "基本每股盈餘" and len(cells) >= 2:
            value_text = cells[1].get_text(strip=True)
            if value_text:
                try:
                    return float(value_text.replace(",", ""))
                except ValueError:
                    return None
    return None


@safe_provider("公開資訊觀測站 (MOPS)")
def _fetch_mops_official(stock_id: str, market_type: str, years_back: int) -> list[EpsRow]:
    typek = _MARKET_TO_TYPEK.get(market_type)
    if not typek:
        raise RuntimeError(f"未知市場別「{market_type}」，無法查詢 MOPS 財報")

    current_year = date.today().year
    rows: list[EpsRow] = []
    for year in range(current_year - years_back, current_year + 1):
        roc_year = year - 1911
        cumulative: dict[int, float] = {}
        for season in (1, 2, 3, 4):
            key = f"eps_mops:{stock_id}:{year}:{season}"
            value = cache.cached_call(
                key,
                config.CACHE_TTL_EPS,
                lambda ry=roc_year, s=season: _fetch_mops_cumulative_eps(stock_id, typek, ry, s),
            )
            if value is not None:
                cumulative[season] = value
        prev = 0.0
        for season in (1, 2, 3, 4):
            if season not in cumulative:
                continue
            quarter_eps = round(cumulative[season] - prev, 2)
            rows.append(EpsRow(year=year, quarter=season, eps=quarter_eps))
            prev = cumulative[season]
    if not rows:
        raise RuntimeError("MOPS 財報查詢無資料")
    rows.sort(key=lambda r: (r.year, r.quarter))
    return rows


def get_eps_history(identity: StockIdentity, years_back: int = 3) -> ProviderResult[list[EpsRow]]:
    start_date = f"{date.today().year - years_back}-01-01"

    result = _fetch_finmind(identity.stock_id, start_date)
    if result.ok:
        return result

    fallback = _fetch_mops_official(identity.stock_id, identity.market_type, years_back)
    if fallback.ok:
        return fallback

    return ProviderResult.failure(
        "FinMind + 官方備援",
        f"FinMind: {result.error}；官方備援: {fallback.error}",
    )
