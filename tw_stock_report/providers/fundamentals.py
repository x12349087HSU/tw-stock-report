"""季度損益表明細 provider（營收/毛利/營業利益/稅前淨利/淨利/EPS）：FinMind 主要來源。

FinMind TaiwanStockFinancialStatements 的各科目本身即為單季數字（非累計），
與 eps.py 使用同一個資料集，但這裡取用更多科目供基本面自檢表使用。
目前僅有 FinMind 一層（無官方備援），失敗時會清楚回報，不影響其他區塊。
"""
from __future__ import annotations

from datetime import date

from .. import cache, config
from ..finmind_client import FinMindError, fetch_dataset
from ..models import QuarterFinancials
from .base import safe_provider

_FIELD_MAP = {
    "Revenue": "revenue",
    "GrossProfit": "gross_profit",
    "OperatingIncome": "operating_income",
    "PreTaxIncome": "pretax_income",
    "EquityAttributableToOwnersOfParent": "net_income",
    "EPS": "eps",
}


def _quarter_of(month: int) -> int:
    return (month - 1) // 3 + 1


@safe_provider("FinMind")
def get_quarterly_financials(stock_id: str, years_back: int = 3) -> list[QuarterFinancials]:
    start_date = f"{date.today().year - years_back}-01-01"

    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockFinancialStatements", data_id=stock_id, start_date=start_date)

    key = f"fundamentals:{stock_id}:{start_date}"
    raw = cache.cached_call(key, config.CACHE_TTL_EPS, _fetch)

    by_period: dict[tuple[int, int], dict] = {}
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
        by_period.setdefault(period, {})[field] = value

    rows: list[QuarterFinancials] = []
    for (year, quarter), fields in sorted(by_period.items()):
        if not {"revenue", "gross_profit", "operating_income", "pretax_income", "net_income", "eps"} <= fields.keys():
            continue  # 科目不齊全（常見於資料剛更新到一半），跳過該季以免誤判
        rows.append(
            QuarterFinancials(
                year=year,
                quarter=quarter,
                revenue=fields["revenue"],
                gross_profit=fields["gross_profit"],
                operating_income=fields["operating_income"],
                pretax_income=fields["pretax_income"],
                net_income=fields["net_income"],
                eps=fields["eps"],
            )
        )
    if not rows:
        raise FinMindError("FinMind 回傳季度損益表資料為空")
    return rows
