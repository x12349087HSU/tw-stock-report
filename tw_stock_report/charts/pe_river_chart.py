"""本益比河流圖：股價 vs. 歷史本益比分位數帶。

做法：用近幾年季度財報算出每一季的 TTM（近四季）EPS，套用到該季結束日之後、
下一季結束日之前的所有交易日（單純用季度切換，未額外模擬財報公佈時間差），
得到每個交易日的「當時本益比」＝收盤價／TTM EPS。再用這條本益比歷史序列算出
10%／30%／50%／70%／90% 分位數，回推成對應的「假設本益比落在該分位時的股價」
畫成河流狀色帶，並把實際收盤價疊在最上面，直觀呈現目前股價相對於自己歷史
本益比區間的位置。

本益比河流圖沒有官方統一公式，分位數的選取（10/30/50/70/90）與四季 TTM 的
簡化假設都是常見但非唯一的做法，報告內文會附註計算方式。
"""
from __future__ import annotations

import io
from datetime import date

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from ..models import PriceBar, QuarterFinancials
from .mpl_setup import COLOR_GRID, COLOR_MUTED, ensure_cjk_font

_PERCENTILES = [10, 30, 50, 70, 90]
_BAND_COLORS = ["#dbe9fb", "#b7d3f6", "#8fb8ef", "#5f97e4", "#2f6fce"]
_PRICE_COLOR = "#1a1a1a"

_QUARTER_END_MONTH_DAY = {1: (3, 31), 2: (6, 30), 3: (9, 30), 4: (12, 31)}


def _quarter_end_date(year: int, quarter: int) -> date:
    month, day = _QUARTER_END_MONTH_DAY[quarter]
    return date(year, month, day)


def _ttm_eps_series(financials: list[QuarterFinancials]) -> list[tuple[date, float]]:
    ordered = sorted(financials, key=lambda r: (r.year, r.quarter))
    out: list[tuple[date, float]] = []
    for i in range(3, len(ordered)):
        window = ordered[i - 3 : i + 1]
        ttm_eps = sum(r.eps for r in window)
        out.append((_quarter_end_date(ordered[i].year, ordered[i].quarter), ttm_eps))
    return out


def render_pe_river_chart(bars: list[PriceBar], financials: list[QuarterFinancials]) -> bytes:
    ensure_cjk_font()
    ttm_series = _ttm_eps_series(financials)
    if not ttm_series or not bars:
        raise ValueError("財報季數或股價資料不足，無法繪製本益比河流圖")

    ordered_bars = sorted(bars, key=lambda b: b.trade_date)
    first_ttm_date = ttm_series[0][0]

    # 對每個交易日，找出「當時有效」的 TTM EPS（最近一個季末日 <= 該交易日）
    aligned_dates: list[date] = []
    aligned_prices: list[float] = []
    aligned_eps: list[float] = []
    ttm_idx = 0
    for bar in ordered_bars:
        if bar.trade_date < first_ttm_date:
            continue
        while ttm_idx + 1 < len(ttm_series) and ttm_series[ttm_idx + 1][0] <= bar.trade_date:
            ttm_idx += 1
        eps = ttm_series[ttm_idx][1]
        if eps <= 0:
            continue  # EPS 為負時本益比沒有意義，跳過該交易日
        aligned_dates.append(bar.trade_date)
        aligned_prices.append(bar.close)
        aligned_eps.append(eps)

    if len(aligned_dates) < 30:
        raise ValueError("可對齊 TTM EPS 的交易日不足，無法繪製本益比河流圖")

    pe_series = [p / e for p, e in zip(aligned_prices, aligned_eps)]
    band_pe_values = np.percentile(pe_series, _PERCENTILES)

    fig, ax = plt.subplots(figsize=(9.2, 4.2))

    band_lines = [[eps * pe for eps in aligned_eps] for pe in band_pe_values]
    for i in range(len(band_lines) - 1):
        ax.fill_between(aligned_dates, band_lines[i], band_lines[i + 1], color=_BAND_COLORS[i], zorder=1)
    for i, (pe, line) in enumerate(zip(band_pe_values, band_lines)):
        ax.plot(aligned_dates, line, color=_BAND_COLORS[min(i, len(_BAND_COLORS) - 1)],
                 linewidth=0.8, alpha=0.9, zorder=2)
        ax.annotate(
            f"{_PERCENTILES[i]}% ({pe:.1f}x)",
            xy=(aligned_dates[-1], line[-1]),
            xytext=(6, 0),
            textcoords="offset points",
            fontsize=7,
            color=COLOR_MUTED,
            va="center",
        )

    ax.plot(aligned_dates, aligned_prices, color=_PRICE_COLOR, linewidth=1.6, label="實際收盤價", zorder=5)

    ax.grid(True, color=COLOR_GRID, linewidth=0.6, zorder=0)
    ax.spines[["top", "right"]].set_visible(False)
    ax.legend(loc="upper left", fontsize=8, frameon=False)
    ax.tick_params(axis="both", labelsize=8)

    ax.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=0, ha="center")

    fig.tight_layout()
    fig.subplots_adjust(right=0.86)
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()
