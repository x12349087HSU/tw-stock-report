"""股價走勢圖：收盤價 + 成交量，標註區間高低點。"""
from __future__ import annotations

import io
from datetime import date, timedelta

import matplotlib.dates as mdates
import matplotlib.pyplot as plt

from ..models import PriceBar
from .mpl_setup import COLOR_GRID, COLOR_MUTED, COLOR_PRIMARY, COLOR_SECONDARY, ensure_cjk_font


def _slice_period(bars: list[PriceBar], months: int) -> list[PriceBar]:
    if not bars:
        return []
    cutoff = bars[-1].trade_date - timedelta(days=months * 31)
    return [b for b in bars if b.trade_date >= cutoff]


def render_price_chart(bars: list[PriceBar], months: int, title: str) -> bytes:
    """畫出指定期間的收盤價（含成交量子圖）與高低點標註，回傳 PNG bytes。"""
    ensure_cjk_font()
    period_bars = _slice_period(bars, months)
    if not period_bars:
        raise ValueError("此期間無股價資料")

    dates = [b.trade_date for b in period_bars]
    closes = [b.close for b in period_bars]
    volumes = [b.volume for b in period_bars]

    high_bar = max(period_bars, key=lambda b: b.high)
    low_bar = min(period_bars, key=lambda b: b.low)

    fig, (ax_price, ax_vol) = plt.subplots(
        2, 1, figsize=(8.6, 3.6), sharex=True, gridspec_kw={"height_ratios": [3, 1]}
    )

    ax_price.plot(dates, closes, color=COLOR_PRIMARY, linewidth=1.6)
    ax_price.set_title(title, fontsize=11, loc="left", color="#222222")
    ax_price.grid(True, color=COLOR_GRID, linewidth=0.6)
    ax_price.spines[["top", "right"]].set_visible(False)

    ax_price.annotate(
        f"高 {high_bar.high:,.1f}",
        xy=(high_bar.trade_date, high_bar.high),
        xytext=(0, 8),
        textcoords="offset points",
        fontsize=8,
        color=COLOR_SECONDARY,
        ha="center",
    )
    ax_price.scatter([high_bar.trade_date], [high_bar.high], color=COLOR_SECONDARY, s=14, zorder=5)

    ax_price.annotate(
        f"低 {low_bar.low:,.1f}",
        xy=(low_bar.trade_date, low_bar.low),
        xytext=(0, -14),
        textcoords="offset points",
        fontsize=8,
        color=COLOR_MUTED,
        ha="center",
    )
    ax_price.scatter([low_bar.trade_date], [low_bar.low], color=COLOR_MUTED, s=14, zorder=5)

    ax_vol.bar(dates, volumes, color=COLOR_PRIMARY, alpha=0.35, width=1.0)
    ax_vol.set_ylabel("成交量", fontsize=8, color=COLOR_MUTED)
    ax_vol.spines[["top", "right"]].set_visible(False)
    ax_vol.tick_params(axis="y", labelsize=7)

    ax_vol.xaxis.set_major_locator(mdates.AutoDateLocator())
    ax_vol.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate(rotation=0, ha="center")

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()
