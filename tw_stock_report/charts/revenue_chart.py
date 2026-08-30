"""月營收長條圖 + YoY 折線（分開子圖呈現，不使用雙 y 軸）。"""
from __future__ import annotations

import io

import matplotlib.pyplot as plt

from ..models import RevenueRow
from .mpl_setup import COLOR_GRID, COLOR_PRIMARY, COLOR_SECONDARY, ensure_cjk_font


def render_revenue_chart(rows: list[RevenueRow]) -> bytes:
    ensure_cjk_font()
    if not rows:
        raise ValueError("無營收資料")

    rows = sorted(rows, key=lambda r: (r.year, r.month))
    labels = [f"{r.year % 100:02d}/{r.month:02d}" for r in rows]
    revenue_billion = [r.revenue / 1_000_000 for r in rows]  # 仟元 -> 十億元
    yoy = [r.yoy_pct for r in rows]

    fig, (ax_rev, ax_yoy) = plt.subplots(2, 1, figsize=(8.6, 3.8), sharex=True, gridspec_kw={"height_ratios": [2, 1]})

    ax_rev.bar(labels, revenue_billion, color=COLOR_PRIMARY, width=0.65)
    ax_rev.set_ylabel("月營收（十億元）", fontsize=8, color="#444444")
    ax_rev.grid(True, axis="y", color=COLOR_GRID, linewidth=0.6)
    ax_rev.spines[["top", "right"]].set_visible(False)

    yoy_x = [labels[i] for i in range(len(rows)) if yoy[i] is not None]
    yoy_y = [yoy[i] for i in range(len(rows)) if yoy[i] is not None]
    ax_yoy.plot(yoy_x, yoy_y, color=COLOR_SECONDARY, linewidth=1.4, marker="o", markersize=2.5)
    ax_yoy.axhline(0, color="#999999", linewidth=0.7)
    ax_yoy.set_ylabel("YoY %", fontsize=8, color="#444444")
    ax_yoy.spines[["top", "right"]].set_visible(False)

    tick_step = max(1, len(labels) // 12)
    for ax in (ax_rev, ax_yoy):
        ax.set_xticks(labels[::tick_step])
        ax.tick_params(axis="x", labelsize=7, rotation=45)
        ax.tick_params(axis="y", labelsize=7)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()
