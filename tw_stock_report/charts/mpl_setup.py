"""matplotlib 中文字型設定，供所有圖表模組共用。"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt

from ..pdf.fonts import find_cjk_font_path

_configured = False


def ensure_cjk_font() -> None:
    global _configured
    if _configured:
        return
    font_path = find_cjk_font_path()
    if font_path:
        fm.fontManager.addfont(font_path)
        family = fm.FontProperties(fname=font_path).get_name()
        plt.rcParams["font.family"] = family
    plt.rcParams["axes.unicode_minus"] = False
    _configured = True


# 圖表配色：與 PDF 主色呼應，維持單一色系、避免花俏漸層
COLOR_PRIMARY = "#1f4e8c"
COLOR_SECONDARY = "#c0521f"
COLOR_GRID = "#d9d9d9"
COLOR_MUTED = "#7a7a7a"
