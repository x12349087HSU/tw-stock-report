"""CJK 字型偵測與 ReportLab 註冊。

優先使用 Windows 內建「微軟正黑體」，不需額外下載字型檔。找不到任何可用字型時
會在報告產生前丟出清楚的例外，而不是默默產出亂碼/方框的 PDF。
"""
from __future__ import annotations

from pathlib import Path

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

FONT_NAME_REGULAR = "TWReportCJK"
FONT_NAME_BOLD = "TWReportCJK-Bold"

_CANDIDATE_FONTS = [
    # (regular, bold, subfont_index)
    (r"C:\Windows\Fonts\msjh.ttc", r"C:\Windows\Fonts\msjhbd.ttc", 0),
    (r"C:\Windows\Fonts\mingliu.ttc", r"C:\Windows\Fonts\mingliu.ttc", 0),
    (r"C:\Windows\Fonts\kaiu.ttf", r"C:\Windows\Fonts\kaiu.ttf", None),
]

_registered = False


class NoCjkFontFoundError(Exception):
    pass


def find_cjk_font_path() -> str | None:
    """回傳第一個存在的中文字型檔路徑（給 matplotlib 使用），找不到則回傳 None。"""
    for regular, _bold, _idx in _CANDIDATE_FONTS:
        if Path(regular).exists():
            return regular
    return None


def register_cjk_fonts() -> tuple[str, str]:
    """向 ReportLab 註冊中文字型，回傳 (regular_name, bold_name)。找不到任何候選字型會拋出例外。"""
    global _registered
    if _registered:
        return FONT_NAME_REGULAR, FONT_NAME_BOLD

    for regular, bold, subfont_index in _CANDIDATE_FONTS:
        if not Path(regular).exists():
            continue
        try:
            if subfont_index is not None:
                pdfmetrics.registerFont(TTFont(FONT_NAME_REGULAR, regular, subfontIndex=subfont_index))
            else:
                pdfmetrics.registerFont(TTFont(FONT_NAME_REGULAR, regular))
            if Path(bold).exists() and bold != regular:
                pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, bold, subfontIndex=subfont_index or 0))
            else:
                # 沒有獨立粗體檔就用同一份字型頂替，仍可正常顯示（只是不會真的變粗）
                pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, regular, subfontIndex=subfont_index or 0))
            _registered = True
            return FONT_NAME_REGULAR, FONT_NAME_BOLD
        except Exception:
            continue

    raise NoCjkFontFoundError(
        "找不到可用的中文字型（已嘗試微軟正黑體/細明體/標楷體）。"
        "請確認 Windows 字型目錄或安裝一套中文字型後再產生報告。"
    )
