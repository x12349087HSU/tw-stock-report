"""共用資料結構。"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Generic, Optional, TypeVar


@dataclass
class StockIdentity:
    stock_id: str
    company_name: str
    aliases: list[str]
    industry_name: str
    market_type: str  # "上市" / "上櫃" / "未知"

    def all_search_names(self) -> list[str]:
        names = [self.company_name, *self.aliases]
        seen: set[str] = set()
        out: list[str] = []
        for n in names:
            n = (n or "").strip()
            if n and n not in seen:
                seen.add(n)
                out.append(n)
        return out


@dataclass
class PriceBar:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class RevenueRow:
    year: int
    month: int
    revenue: float  # 新台幣仟元
    mom_pct: Optional[float] = None
    yoy_pct: Optional[float] = None


@dataclass
class EpsRow:
    year: int
    quarter: int  # 1-4
    eps: float


@dataclass
class QuarterFinancials:
    year: int
    quarter: int
    revenue: float
    gross_profit: float
    operating_income: float
    pretax_income: float
    net_income: float  # 歸屬於母公司業主淨利
    eps: float


@dataclass
class QuarterBalance:
    year: int
    quarter: int
    total_assets: float
    liabilities: float
    equity: float  # 歸屬於母公司業主權益


@dataclass
class QuarterCashFlow:
    year: int
    quarter: int
    operating_cash_flow: float
    interest_expense: float


@dataclass
class ChecklistItem:
    tier: int
    tier_name: str
    name: str
    passed: Optional[bool]  # None = 資料不足，無法判定
    detail: str


@dataclass
class NewsItem:
    title: str
    publish_date: Optional[date]
    source: str
    url: str
    snippet: str = ""
    matched_keyword: str = ""


@dataclass
class RatingItem:
    source_title: str
    source_url: str
    publish_date: Optional[date]
    institution: str = ""
    rating: str = ""
    target_price: Optional[float] = None
    note: str = ""


@dataclass
class SourceStatus:
    module: str  # e.g. "price", "revenue", "eps", "news", "rating"
    source_used: str  # e.g. "FinMind", "TWSE OpenAPI", "MOPS", "MoneyDJ+鉅亨網", "無"
    ok: bool
    message: str = ""


T = TypeVar("T")


@dataclass
class ProviderResult(Generic[T]):
    """所有 provider 的統一回傳型別：永不對外拋出例外。"""

    ok: bool
    data: Optional[T]
    source_name: str
    error: str = ""

    @staticmethod
    def success(data: T, source_name: str) -> "ProviderResult[T]":
        return ProviderResult(ok=True, data=data, source_name=source_name, error="")

    @staticmethod
    def failure(source_name: str, error: str) -> "ProviderResult[T]":
        return ProviderResult(ok=False, data=None, source_name=source_name, error=error)


@dataclass
class ReportData:
    identity: StockIdentity
    generated_at: date

    price_bars_1y: list[PriceBar] = field(default_factory=list)
    price_bars_extended: list[PriceBar] = field(default_factory=list)  # 涵蓋 1 年以上，供均線暖身/本益比河流圖使用
    price_high_1y: Optional[PriceBar] = None
    price_low_1y: Optional[PriceBar] = None

    revenue_rows_24m: list[RevenueRow] = field(default_factory=list)
    revenue_summary_text: str = ""

    eps_rows_8q: list[EpsRow] = field(default_factory=list)
    eps_rows_annual: list[EpsRow] = field(default_factory=list)
    eps_summary_text: str = ""

    quarterly_financials: list[QuarterFinancials] = field(default_factory=list)  # 供本益比河流圖使用

    industry_news: list[NewsItem] = field(default_factory=list)
    stock_news: list[NewsItem] = field(default_factory=list)
    industry_trend_text: str = ""
    stock_highlight_text: str = ""

    ratings: list[RatingItem] = field(default_factory=list)

    checklist_items: list[ChecklistItem] = field(default_factory=list)

    source_statuses: list[SourceStatus] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
