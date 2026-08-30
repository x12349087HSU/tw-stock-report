"""現金流量表 provider（營業活動現金流/利息費用）：FinMind 主要來源。

FinMind 的現金流量表科目是「當年度累計數」（Q1=Q1、Q2=上半年累計、Q3=前三季累計、
Q4=全年累計），與損益表科目（單季）不同，因此這裡需要用累計值相減換算成單季數字，
邏輯與 eps.py 官方備援換算 MOPS 累計 EPS 相同。

目前僅有 FinMind 一層（無官方備援），失敗時會清楚回報，不影響其他區塊。
"""
from __future__ import annotations

from datetime import date

from .. import cache, config
from ..finmind_client import FinMindError, fetch_dataset
from ..models import QuarterCashFlow
from .base import safe_provider

_FIELD_MAP = {
    "CashFlowsFromOperatingActivities": "operating_cash_flow",
    "NetCashInflowFromOperatingActivities": "operating_cash_flow",  # 不同期別/版本科目名稱可能不同，取有值者
    "InterestExpense": "interest_expense",
}


def _quarter_of(month: int) -> int:
    return (month - 1) // 3 + 1


@safe_provider("FinMind")
def get_quarterly_cash_flow(stock_id: str, years_back: int = 3) -> list[QuarterCashFlow]:
    start_date = f"{date.today().year - years_back}-01-01"

    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockCashFlowsStatement", data_id=stock_id, start_date=start_date)

    key = f"cash_flow:{stock_id}:{start_date}"
    raw = cache.cached_call(key, config.CACHE_TTL_EPS, _fetch)

    cumulative_by_period: dict[tuple[int, int], dict] = {}
    for item in raw:
        field = _FIELD_MAP.get(item.get("type"))
        if not field:
            continue
        try:
            d = date.fromisoformat(item["date"])
            value = float(item["value"])
        except (KeyError, ValueError, TypeError):
            continue
        period = (d.year, _quarter_of(d.month))
        cumulative_by_period.setdefault(period, {}).setdefault(field, value)

    rows: list[QuarterCashFlow] = []
    prev_year: int | None = None
    prev_cum = {"operating_cash_flow": 0.0, "interest_expense": 0.0}
    for (year, quarter), fields in sorted(cumulative_by_period.items()):
        if "operating_cash_flow" not in fields:
            continue
        if year != prev_year:
            prev_cum = {"operating_cash_flow": 0.0, "interest_expense": 0.0}
            prev_year = year

        cum_ocf = fields["operating_cash_flow"]
        cum_interest = fields.get("interest_expense", prev_cum["interest_expense"])

        rows.append(
            QuarterCashFlow(
                year=year,
                quarter=quarter,
                operating_cash_flow=round(cum_ocf - prev_cum["operating_cash_flow"], 2),
                interest_expense=round(cum_interest - prev_cum["interest_expense"], 2),
            )
        )
        prev_cum = {"operating_cash_flow": cum_ocf, "interest_expense": cum_interest}

    if not rows:
        raise FinMindError("FinMind 回傳現金流量表資料為空")
    return rows
