"""基本面自檢表：四層核心成長動能評核邏輯。

每一項的判定公式都寫在對應函式的 docstring／detail 文字中，供使用者核對，
因為原始需求中部分指標（現金轉換率、利息保障倍數、ROE/ROA 穩定度、獲利是否來自本業）
在實務上並無單一標準公式，這裡採用財務教學上常見的定義並在報告中明確揭露，
而不是隱藏假設。任何資料不足以判定的項目都回傳 passed=None，不猜測結果。
"""
from __future__ import annotations

from ..models import ChecklistItem, QuarterBalance, QuarterCashFlow, QuarterFinancials

TIER1 = "第一層：核心成長動能"
TIER2 = "第二層：獲利品質（ROE / ROA）"
TIER3 = "第三層：財務體質"
TIER4 = "第四層：獲利能力趨勢"


def _by_period(rows: list) -> dict[tuple[int, int], object]:
    return {(r.year, r.quarter): r for r in rows}


def _prev_year_quarter(year: int, quarter: int) -> tuple[int, int]:
    return year - 1, quarter


def _fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def _revenue_growth_streak(financials: list[QuarterFinancials]) -> ChecklistItem:
    by_period = _by_period(financials)
    ordered = sorted(financials, key=lambda r: (r.year, r.quarter))
    yoy_flags: list[tuple[tuple[int, int], float]] = []
    for r in ordered:
        prev = by_period.get(_prev_year_quarter(r.year, r.quarter))
        if prev is None or not prev.revenue:
            continue
        yoy = (r.revenue - prev.revenue) / abs(prev.revenue) * 100
        yoy_flags.append(((r.year, r.quarter), yoy))

    if len(yoy_flags) < 3:
        return ChecklistItem(1, TIER1, "營收成長：單季營收年增率 > 0，連三季達標", None, "可計算年增率的季數不足 3 季，暫無法判定。")

    last3 = yoy_flags[-3:]
    passed = all(v > 0 for _, v in last3)
    detail = "近三季 YoY：" + "、".join(f"{y}Q{q} {_fmt_pct(v)}" for (y, q), v in last3)
    return ChecklistItem(1, TIER1, "營收成長：單季營收年增率 > 0，連三季達標", passed, detail)


def _eps_growth_streak(financials: list[QuarterFinancials]) -> ChecklistItem:
    by_period = _by_period(financials)
    ordered = sorted(financials, key=lambda r: (r.year, r.quarter))
    yoy_flags: list[tuple[tuple[int, int], float]] = []
    for r in ordered:
        prev = by_period.get(_prev_year_quarter(r.year, r.quarter))
        if prev is None or not prev.eps:
            continue
        yoy = (r.eps - prev.eps) / abs(prev.eps) * 100
        yoy_flags.append(((r.year, r.quarter), yoy))

    if len(yoy_flags) < 2:
        return ChecklistItem(1, TIER1, "EPS 成長：單季 EPS 年增率 > 0，連兩季達標", None, "可計算年增率的季數不足 2 季，暫無法判定。")

    last2 = yoy_flags[-2:]
    passed = all(v > 0 for _, v in last2)
    detail = "近兩季 YoY：" + "、".join(f"{y}Q{q} {_fmt_pct(v)}" for (y, q), v in last2)
    return ChecklistItem(1, TIER1, "EPS 成長：單季 EPS 年增率 > 0，連兩季達標", passed, detail)


def _profit_from_core_business(financials: list[QuarterFinancials]) -> ChecklistItem:
    """獲利來自本業：定義為「營業利益 / 稅前淨利」比重 >= 50%（最新一季）。"""
    if not financials:
        return ChecklistItem(1, TIER1, "獲利來自本業（營業利益 / 稅前淨利 ≥ 50%）", None, "無季度損益表資料。")
    latest = sorted(financials, key=lambda r: (r.year, r.quarter))[-1]
    if latest.pretax_income == 0:
        return ChecklistItem(1, TIER1, "獲利來自本業（營業利益 / 稅前淨利 ≥ 50%）", None, "最新一季稅前淨利為 0，比率無法計算。")
    ratio = latest.operating_income / latest.pretax_income * 100
    passed = latest.operating_income > 0 and ratio >= 50
    detail = f"{latest.year}Q{latest.quarter} 營業利益 {latest.operating_income/1e8:,.1f} 億元／稅前淨利 {latest.pretax_income/1e8:,.1f} 億元，佔比 {ratio:.1f}%。"
    return ChecklistItem(1, TIER1, "獲利來自本業（營業利益 / 稅前淨利 ≥ 50%）", passed, detail)


def _ttm_series(values: list[float]) -> list[float | None]:
    """回傳每個位置的「trailing 4 季加總」，前 3 個位置資料不足回傳 None。"""
    out: list[float | None] = []
    for i in range(len(values)):
        if i < 3:
            out.append(None)
        else:
            out.append(sum(values[i - 3 : i + 1]))
    return out


def _roe_roa(
    financials: list[QuarterFinancials], balance: list[QuarterBalance], threshold: float, tier: int, label: str, ratio_key: str
) -> ChecklistItem:
    fin_by_period = _by_period(financials)
    bal_by_period = _by_period(balance)
    periods = sorted(set(fin_by_period) & set(bal_by_period))
    if len(periods) < 4:
        return ChecklistItem(
            2, TIER2, label, None, f"同時具備損益表與資產負債表的季數僅 {len(periods)} 季，不足以計算 TTM，暫無法判定。"
        )

    # 先用「全部可用季數」計算 TTM 序列（每個點都需要往前 3 季當基期），
    # 最後才取最新 8 個有效值，避免因為預先裁切成 8 季而少掉可用的基期資料。
    net_incomes = [fin_by_period[p].net_income for p in periods]
    ttm_ni = _ttm_series(net_incomes)

    ratios: list[float] = []
    for i, p in enumerate(periods):
        if ttm_ni[i] is None:
            continue
        base_period_idx = i - 3
        base = getattr(bal_by_period[periods[base_period_idx]], ratio_key)
        curr = getattr(bal_by_period[p], ratio_key)
        avg_base = (base + curr) / 2
        if avg_base == 0:
            continue
        ratios.append(ttm_ni[i] / avg_base * 100)
    ratios = ratios[-8:]

    if len(ratios) < 3:
        return ChecklistItem(2, TIER2, label, None, "可計算的 TTM 比率季數不足，暫無法判定。")

    avg_ratio = sum(ratios) / len(ratios)
    spread = max(ratios) - min(ratios)
    stable = spread <= max(avg_ratio * 0.35, 5)
    passed = avg_ratio >= threshold and stable
    detail = (
        f"近 {len(ratios)} 季 TTM 平均 {avg_ratio:.1f}%（範圍 {min(ratios):.1f}%～{max(ratios):.1f}%）。"
        f"門檻 {threshold:.0f}%，{'穩定' if stable else '波動較大'}。"
    )
    return ChecklistItem(2, TIER2, label, passed, detail)


def _debt_ratio(balance: list[QuarterBalance]) -> ChecklistItem:
    if not balance:
        return ChecklistItem(3, TIER3, "負債比 < 50%", None, "無資產負債表資料。")
    latest = sorted(balance, key=lambda r: (r.year, r.quarter))[-1]
    if latest.total_assets == 0:
        return ChecklistItem(3, TIER3, "負債比 < 50%", None, "最新一季資產總額為 0，無法計算。")
    ratio = latest.liabilities / latest.total_assets * 100
    passed = ratio < 50
    detail = f"{latest.year}Q{latest.quarter} 負債比 {ratio:.1f}%（負債 {latest.liabilities/1e8:,.0f} 億／資產 {latest.total_assets/1e8:,.0f} 億）。"
    return ChecklistItem(3, TIER3, "負債比 < 50%", passed, detail)


def _interest_coverage(financials: list[QuarterFinancials], cashflow: list[QuarterCashFlow]) -> ChecklistItem:
    """利息保障倍數 = TTM (稅前淨利 + 利息費用) / TTM 利息費用。"""
    fin_by_period = _by_period(financials)
    cf_by_period = _by_period(cashflow)
    periods = sorted(set(fin_by_period) & set(cf_by_period))
    if len(periods) < 4:
        return ChecklistItem(3, TIER3, "利息保障倍數 > 5 倍", None, "可用季數不足 4 季，暫無法計算 TTM 利息保障倍數。")

    last4 = periods[-4:]
    ttm_pretax = sum(fin_by_period[p].pretax_income for p in last4)
    ttm_interest = sum(cf_by_period[p].interest_expense for p in last4)
    if ttm_interest <= 0:
        return ChecklistItem(
            3, TIER3, "利息保障倍數 > 5 倍", True, "近 4 季利息費用揭露為 0 或極低，實質無利息負擔壓力（視為通過）。"
        )
    coverage = (ttm_pretax + ttm_interest) / ttm_interest
    passed = coverage > 5
    detail = f"近 4 季 TTM 利息保障倍數約 {coverage:.1f} 倍（稅前淨利 {ttm_pretax/1e8:,.0f} 億＋利息費用 {ttm_interest/1e8:,.0f} 億 ／ 利息費用）。"
    return ChecklistItem(3, TIER3, "利息保障倍數 > 5 倍", passed, detail)


def _operating_cash_flow_positive(cashflow: list[QuarterCashFlow]) -> ChecklistItem:
    if not cashflow:
        return ChecklistItem(3, TIER3, "營業現金流 > 0", None, "無現金流量表資料。")
    ordered = sorted(cashflow, key=lambda r: (r.year, r.quarter))
    latest = ordered[-1]
    recent4 = ordered[-4:]
    all_positive = all(r.operating_cash_flow > 0 for r in recent4)
    passed = latest.operating_cash_flow > 0
    detail = f"{latest.year}Q{latest.quarter} 營業現金流 {latest.operating_cash_flow/1e8:,.1f} 億元。近 4 季{'皆為正數' if all_positive else '並非每季皆為正數'}。"
    return ChecklistItem(3, TIER3, "營業現金流 > 0", passed, detail)


def _cash_conversion_rate(financials: list[QuarterFinancials], cashflow: list[QuarterCashFlow]) -> ChecklistItem:
    """現金轉換率 = 營業現金流 / 稅後淨利（歸屬母公司），長期（近 8 季平均）> 80%。"""
    fin_by_period = _by_period(financials)
    cf_by_period = _by_period(cashflow)
    periods = sorted(set(fin_by_period) & set(cf_by_period))
    if len(periods) < 4:
        return ChecklistItem(3, TIER3, "現金轉換率（營業現金流／淨利）長期 > 80%", None, "可用季數不足，暫無法判定。")

    periods = periods[-8:]
    ratios = []
    for p in periods:
        ni = fin_by_period[p].net_income
        if ni <= 0:
            continue
        ratios.append(cf_by_period[p].operating_cash_flow / ni * 100)

    if len(ratios) < 3:
        return ChecklistItem(3, TIER3, "現金轉換率（營業現金流／淨利）長期 > 80%", None, "可用季數不足，暫無法判定。")

    avg_ratio = sum(ratios) / len(ratios)
    passed = avg_ratio > 80
    detail = f"近 {len(ratios)} 季平均現金轉換率約 {avg_ratio:.0f}%（單季介於 {min(ratios):.0f}%～{max(ratios):.0f}%）。"
    return ChecklistItem(3, TIER3, "現金轉換率（營業現金流／淨利）長期 > 80%", passed, detail)


def _margin_trend(financials: list[QuarterFinancials], numerator_key: str, label: str) -> ChecklistItem:
    ordered = sorted(financials, key=lambda r: (r.year, r.quarter))
    by_period = _by_period(financials)
    if len(ordered) < 5:
        return ChecklistItem(4, TIER4, label, None, "可用季數不足，暫無法比較年增趨勢。")

    latest = ordered[-1]
    prev_year = by_period.get(_prev_year_quarter(latest.year, latest.quarter))
    if prev_year is None or not prev_year.revenue or not latest.revenue:
        return ChecklistItem(4, TIER4, label, None, "缺少去年同季資料，暫無法比較。")

    latest_margin = getattr(latest, numerator_key) / latest.revenue * 100
    prev_margin = getattr(prev_year, numerator_key) / prev_year.revenue * 100
    diff = latest_margin - prev_margin
    passed = diff >= -0.5  # 容許極小幅波動仍視為「持平」
    detail = (
        f"{latest.year}Q{latest.quarter} {latest_margin:.1f}% vs 去年同季 {prev_margin:.1f}%，"
        f"{'持平或提升' if passed else '較去年同期下滑'}（差異 {diff:+.1f} 個百分點）。"
    )
    return ChecklistItem(4, TIER4, label, passed, detail)


def evaluate_checklist(
    financials: list[QuarterFinancials],
    balance: list[QuarterBalance],
    cashflow: list[QuarterCashFlow],
) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []

    items.append(_revenue_growth_streak(financials))
    items.append(_eps_growth_streak(financials))
    items.append(_profit_from_core_business(financials))

    items.append(_roe_roa(financials, balance, threshold=15, tier=2, label="ROE：近 8 季 TTM 維持 15% 以上且穩定", ratio_key="equity"))
    items.append(_roe_roa(financials, balance, threshold=8, tier=2, label="ROA：近 8 季 TTM 維持 8% 以上且穩定", ratio_key="total_assets"))

    items.append(_debt_ratio(balance))
    items.append(_interest_coverage(financials, cashflow))
    items.append(_operating_cash_flow_positive(cashflow))
    items.append(_cash_conversion_rate(financials, cashflow))

    items.append(_margin_trend(financials, "gross_profit", "毛利率：持平或增加（較去年同季）"))
    items.append(_margin_trend(financials, "operating_income", "營業利益率：持平或增加（較去年同季）"))

    return items
