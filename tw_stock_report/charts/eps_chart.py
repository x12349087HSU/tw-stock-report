"""近 8 季 EPS 長條圖。"""
from __future__ import annotations

import io

import matplotlib.pyplot as plt

from ..models import EpsRow
from .mpl_setup import COLOR_GRID, COLOR_PRIMARY, ensure_cjk_font


def render_eps_chart(rows: list[EpsRow]) -> bytes:
    ensure_cjk_font()
    if not rows:
        raise ValueError("無 EPS 資料")

    rows = sorted(rows, key=lambda r: (r.year, r.quarter))[-8:]
    labels = [f"{r.year % 100:02d}Q{r.quarter}" for r in rows]
    values = [r.eps for r in rows]

    fig, ax = plt.subplots(figsize=(8.6, 3.0))
    bars = ax.bar(labels, values, color=COLOR_PRIMARY, width=0.55)
    ax.grid(True, axis="y", color=COLOR_GRID, linewidth=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_ylabel("EPS（元）", fontsize=8, color="#444444")
    ax.tick_params(axis="both", labelsize=8)

    for bar, value in zip(bars, values):
        ax.annotate(
            f"{value:.2f}",
            xy=(bar.get_x() + bar.get_width() / 2, bar.get_height()),
            xytext=(0, 3),
            textcoords="offset points",
            ha="center",
            fontsize=7.5,
            color="#333333",
        )

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()
