"""月營收 provider：FinMind 主要 + 公開資訊觀測站(MOPS)月營收查詢官方備援。"""
from __future__ import annotations

from datetime import date

from bs4 import BeautifulSoup

from .. import cache, config, http_client
from ..finmind_client import FinMindError, fetch_dataset
from ..models import ProviderResult, RevenueRow, StockIdentity
from .base import safe_provider


def _compute_mom_yoy(rows: list[RevenueRow]) -> list[RevenueRow]:
    rows = sorted(rows, key=lambda r: (r.year, r.month))
    by_ym = {(r.year, r.month): r for r in rows}
    for r in rows:
        prev_month = (r.year, r.month - 1) if r.month > 1 else (r.year - 1, 12)
        prev_year = (r.year - 1, r.month)
        prev = by_ym.get(prev_month)
        if prev and prev.revenue:
            r.mom_pct = round((r.revenue - prev.revenue) / prev.revenue * 100, 2)
        prev_y = by_ym.get(prev_year)
        if prev_y and prev_y.revenue:
            r.yoy_pct = round((r.revenue - prev_y.revenue) / prev_y.revenue * 100, 2)
    return rows


@safe_provider("FinMind")
def _fetch_finmind(stock_id: str, start_date: str) -> list[RevenueRow]:
    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockMonthRevenue", data_id=stock_id, start_date=start_date)

    key = f"revenue:{stock_id}:{start_date}"
    raw = cache.cached_call(key, config.CACHE_TTL_REVENUE, _fetch)

    rows: list[RevenueRow] = []
    for item in raw:
        try:
            rows.append(
                RevenueRow(
                    year=int(item["revenue_year"]),
                    month=int(item["revenue_month"]),
                    revenue=float(item["revenue"]) / 1000.0,  # FinMind 單位為元，轉為仟元與 MOPS 對齊
                )
            )
        except (KeyError, ValueError, TypeError):
            continue
    if not rows:
        raise FinMindError("FinMind 回傳月營收資料為空")
    return _compute_mom_yoy(rows)


def _mops_month_url(stock_id: str, roc_year: int, month: int) -> str:
    return (
        "https://mopsov.twse.com.tw/mops/web/ajax_t05st10_ifrs"
        f"?firstin=true&off=1&step=0&co_id={stock_id}&year={roc_year}&month={month:02d}"
    )


def _fetch_mops_month(stock_id: str, roc_year: int, month: int) -> RevenueRow | None:
    url = _mops_month_url(stock_id, roc_year, month)
    resp = http_client.get(url)
    soup = BeautifulSoup(resp.text, "lxml")
    label_to_value: dict[str, str] = {}
    for tr in soup.select("table.hasBorder tr"):
        th = tr.find("th")
        td = tr.find("td")
        if th and td:
            label_to_value[th.get_text(strip=True)] = td.get_text(strip=True).replace("\xa0", "")

    this_month_raw = label_to_value.get("本月", "")
    if not this_month_raw:
        return None
    try:
        revenue = float(this_month_raw.replace(",", ""))
    except ValueError:
        return None
    row = RevenueRow(year=roc_year + 1911, month=month, revenue=revenue)
    yoy_raw = label_to_value.get("增減百分比")
    if yoy_raw:
        try:
            row.yoy_pct = float(yoy_raw.replace(",", ""))
        except ValueError:
            pass
    return row


@safe_provider("公開資訊觀測站 (MOPS)")
def _fetch_mops_official(stock_id: str, months: int) -> list[RevenueRow]:
    today = date.today()
    rows: list[RevenueRow] = []
    y, m = today.year, today.month
    for _ in range(months):
        m -= 1
        if m == 0:
            m = 12
            y -= 1
        roc_year = y - 1911
        key = f"revenue_mops:{stock_id}:{y}-{m:02d}"
        row = cache.cached_call(
            key, config.CACHE_TTL_REVENUE, lambda ry=roc_year, mm=m: _fetch_mops_month(stock_id, ry, mm)
        )
        if row:
            rows.append(row)
    if not rows:
        raise RuntimeError("MOPS 月營收查詢無資料")
    return _compute_mom_yoy(rows)


def get_monthly_revenue(identity: StockIdentity, months: int = 24) -> ProviderResult[list[RevenueRow]]:
    start = date.today().replace(day=1)
    start_year = start.year - (months // 12) - 1
    start_date = f"{start_year}-01-01"

    result = _fetch_finmind(identity.stock_id, start_date)
    if result.ok:
        return result

    fallback = _fetch_mops_official(identity.stock_id, months)
    if fallback.ok:
        return fallback

    return ProviderResult.failure(
        "FinMind + 官方備援",
        f"FinMind: {result.error}；官方備援: {fallback.error}",
    )
