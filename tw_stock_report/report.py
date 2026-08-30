"""Orchestrator：輸入股票代號/名稱 -> 彙整全部資料 -> 產出 PDF。

CLI 與 Streamlit 都只呼叫這裡的 generate_report，確保兩個介面行為一致。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from . import config
from .analysis import checklist as checklist_engine
from .identity import IdentityNotFound, resolve
from .models import EpsRow, ReportData, SourceStatus
from .pdf.builder import build_pdf
from .providers import balance_sheet as balance_sheet_provider
from .providers import cash_flow as cash_flow_provider
from .providers import eps as eps_provider
from .providers import fundamentals as fundamentals_provider
from .providers import price as price_provider
from .providers import revenue as revenue_provider
from .providers.news import aggregator as news_aggregator
from .providers.rating import aggregator as rating_aggregator


@dataclass
class ReportResult:
    pdf_bytes: bytes
    pdf_path: str
    data: ReportData


def _revenue_summary(rows) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: (r.year, r.month))
    latest = rows[-1]
    parts = [f"最新月營收（{latest.year}年{latest.month}月）為 {latest.revenue:,.0f} 仟元。"]
    if latest.mom_pct is not None:
        direction = "增加" if latest.mom_pct >= 0 else "減少"
        parts.append(f"較上月{direction} {abs(latest.mom_pct):.1f}%。")
    if latest.yoy_pct is not None:
        direction = "成長" if latest.yoy_pct >= 0 else "衰退"
        parts.append(f"較去年同期{direction} {abs(latest.yoy_pct):.1f}%。")
    recent = [r for r in rows[-6:] if r.yoy_pct is not None]
    if len(recent) >= 3:
        avg_yoy = sum(r.yoy_pct for r in recent) / len(recent)
        trend = "呈現成長趨勢" if avg_yoy > 0 else "呈現衰退趨勢"
        parts.append(f"近 {len(recent)} 個月平均年增率約 {avg_yoy:.1f}%，{trend}。")
    return "".join(parts)


def _eps_summary(rows) -> str:
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: (r.year, r.quarter))
    latest = rows[-1]
    parts = [f"最新一季（{latest.year}Q{latest.quarter}）EPS 為 {latest.eps:.2f} 元。"]
    if len(rows) >= 2:
        prev = rows[-2]
        if prev.eps:
            qoq = (latest.eps - prev.eps) / abs(prev.eps) * 100
            direction = "增加" if qoq >= 0 else "減少"
            parts.append(f"較上一季{direction} {abs(qoq):.1f}%。")
    if len(rows) >= 5:
        yoy_ref = rows[-5]
        if yoy_ref.eps:
            yoy = (latest.eps - yoy_ref.eps) / abs(yoy_ref.eps) * 100
            direction = "成長" if yoy >= 0 else "衰退"
            parts.append(f"較去年同季{direction} {abs(yoy):.1f}%。")
    return "".join(parts)


def _annual_eps(rows: list[EpsRow]) -> list[EpsRow]:
    by_year: dict[int, list[EpsRow]] = {}
    for r in rows:
        by_year.setdefault(r.year, []).append(r)
    annual: list[EpsRow] = []
    for year, quarter_rows in sorted(by_year.items()):
        if len(quarter_rows) == 4:
            annual.append(EpsRow(year=year, quarter=0, eps=round(sum(r.eps for r in quarter_rows), 2)))
    return annual


def _news_summaries(stock_news, industry_news, identity) -> tuple[str, str]:
    if stock_news:
        titles = "；".join(n.title for n in stock_news[:3])
        stock_text = f"近期與{identity.company_name}相關的公開新聞焦點包括：{titles}。"
    else:
        stock_text = ""

    if industry_news:
        titles = "；".join(n.title for n in industry_news[:3])
        industry_text = f"{identity.industry_name}產業近期公開新聞焦點包括：{titles}。"
    elif stock_news:
        industry_text = (
            f"個股新聞數量已足夠，未另外查詢產業層級新聞；"
            f"{identity.industry_name}產業趨勢可參考下方個股新聞中提及之產業動態。"
        )
    else:
        industry_text = ""
    return industry_text, stock_text


def generate_report(user_input: str) -> ReportResult:
    try:
        identity = resolve(user_input)
    except IdentityNotFound:
        raise

    data = ReportData(identity=identity, generated_at=date.today())
    statuses: list[SourceStatus] = []

    price_result = price_provider.get_price_history(identity, months=13)
    statuses.append(SourceStatus("股價", price_result.source_name, price_result.ok, price_result.error))
    if price_result.ok:
        data.price_bars_1y = price_result.data
        data.price_high_1y = max(price_result.data, key=lambda b: b.high)
        data.price_low_1y = min(price_result.data, key=lambda b: b.low)

    revenue_result = revenue_provider.get_monthly_revenue(identity, months=24)
    statuses.append(SourceStatus("月營收", revenue_result.source_name, revenue_result.ok, revenue_result.error))
    if revenue_result.ok:
        data.revenue_rows_24m = revenue_result.data
        data.revenue_summary_text = _revenue_summary(revenue_result.data)

    eps_result = eps_provider.get_eps_history(identity, years_back=3)
    statuses.append(SourceStatus("EPS", eps_result.source_name, eps_result.ok, eps_result.error))
    if eps_result.ok:
        all_eps = sorted(eps_result.data, key=lambda r: (r.year, r.quarter))
        data.eps_rows_8q = all_eps[-8:]
        data.eps_rows_annual = _annual_eps(all_eps)
        data.eps_summary_text = _eps_summary(all_eps)

    stock_news, industry_news, news_errors = news_aggregator.gather_all_news(identity)
    data.stock_news = stock_news
    data.industry_news = industry_news
    news_ok = bool(stock_news or industry_news)
    statuses.append(
        SourceStatus(
            "新聞",
            "FinMind + 鉅亨網",
            news_ok,
            "；".join(news_errors) if news_errors else "",
        )
    )
    data.industry_trend_text, data.stock_highlight_text = _news_summaries(stock_news, industry_news, identity)
    if news_errors:
        data.warnings.extend(news_errors)

    ratings, rating_errors = rating_aggregator.gather_ratings(identity)
    data.ratings = ratings
    statuses.append(
        SourceStatus(
            "目標價/評等",
            "鉅亨網（規則式擷取）",
            bool(ratings),
            "；".join(rating_errors) if rating_errors else ("查無可辨識之目標價/評等資訊" if not ratings else ""),
        )
    )
    if rating_errors:
        data.warnings.extend(rating_errors)

    fundamentals_result = fundamentals_provider.get_quarterly_financials(identity.stock_id, years_back=3)
    balance_result = balance_sheet_provider.get_quarterly_balance_sheet(identity.stock_id, years_back=3)
    cashflow_result = cash_flow_provider.get_quarterly_cash_flow(identity.stock_id, years_back=3)

    checklist_ok = fundamentals_result.ok and balance_result.ok and cashflow_result.ok
    checklist_errors = [
        r.error for r in (fundamentals_result, balance_result, cashflow_result) if not r.ok
    ]
    statuses.append(
        SourceStatus(
            "基本面自檢表",
            "FinMind（季度財報）",
            checklist_ok,
            "；".join(checklist_errors) if checklist_errors else "",
        )
    )
    data.checklist_items = checklist_engine.evaluate_checklist(
        fundamentals_result.data or [],
        balance_result.data or [],
        cashflow_result.data or [],
    )

    data.source_statuses = statuses

    pdf_bytes = build_pdf(data)
    filename = f"{identity.stock_id}_{identity.company_name}_{data.generated_at.isoformat()}.pdf"
    pdf_path = config.REPORTS_DIR / filename
    pdf_path.write_bytes(pdf_bytes)

    return ReportResult(pdf_bytes=pdf_bytes, pdf_path=str(pdf_path), data=data)
