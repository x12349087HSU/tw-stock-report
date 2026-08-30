"""資產負債表 provider（資產總額/負債總額/歸屬母公司權益）：FinMind 主要來源。

資產負債表科目本身就是「期末餘額」快照，不需要像損益表一樣做累計轉單季的處理。
目前僅有 FinMind 一層（無官方備援），失敗時會清楚回報，不影響其他區塊。
"""
from __future__ import annotations

from datetime import date

from .. import cache, config
from ..finmind_client import FinMindError, fetch_dataset
from ..models import QuarterBalance
from .base import safe_provider

_FIELD_MAP = {
    "TotalAssets": "total_assets",
    "Liabilities": "liabilities",
    "EquityAttributableToOwnersOfParent": "equity",
}


def _quarter_of(month: int) -> int:
    return (month - 1) // 3 + 1


@safe_provider("FinMind")
def get_quarterly_balance_sheet(stock_id: str, years_back: int = 3) -> list[QuarterBalance]:
    start_date = f"{date.today().year - years_back}-01-01"

    def _fetch() -> list[dict]:
        return fetch_dataset("TaiwanStockBalanceSheet", data_id=stock_id, start_date=start_date)

    key = f"balance_sheet:{stock_id}:{start_date}"
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

    rows: list[QuarterBalance] = []
    for (year, quarter), fields in sorted(by_period.items()):
        if not {"total_assets", "liabilities", "equity"} <= fields.keys():
            continue
        rows.append(
            QuarterBalance(
                year=year,
                quarter=quarter,
                total_assets=fields["total_assets"],
                liabilities=fields["liabilities"],
                equity=fields["equity"],
            )
        )
    if not rows:
        raise FinMindError("FinMind 回傳資產負債表資料為空")
    return rows
