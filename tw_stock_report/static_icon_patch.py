"""在啟動時修補 Streamlit 套件本身送出的靜態 index.html / favicon.png。

背景：st.set_page_config(page_icon=...) 只會在瀏覽器分頁「JS 執行之後」動態更新
favicon，Streamlit 原始送出的 index.html 裡永遠是它自帶的 Streamlit 圖示、且完全
沒有 <link rel="apple-touch-icon">。iOS「加入主畫面」讀取的正是這份最原始的 HTML
（在任何 JS 執行之前），所以先前用 JS 動態插入 apple-touch-icon 的做法對「加入主
畫面」這個情境完全沒有效果——這裡直接覆寫 Streamlit 套件內的靜態檔案，確保從
第一個 byte 開始送出的就是我們自己的圖示與標籤。

冪等設計：用一個標記字串檢查是否已經修補過，避免每次重新整理都重複寫入 index.html；
favicon.png 每次都用內容比對，不同才覆寫，避免不必要的磁碟寫入。任何步驟失敗
（例如雲端環境沒有寫入權限）都只記錄、不拋出例外，不能讓整個 App 因此掛掉。
"""
from __future__ import annotations

import base64
import logging
from pathlib import Path

logger = logging.getLogger("tw_stock_report.static_icon_patch")

_MARKER = "<!-- tw-stock-report-icon-patch -->"


def _streamlit_static_dir() -> Path | None:
    try:
        import streamlit

        return Path(streamlit.__file__).resolve().parent / "static"
    except Exception:
        return None


def patch_streamlit_static_assets(icon_dir: Path) -> None:
    static_dir = _streamlit_static_dir()
    if static_dir is None or not static_dir.exists():
        return

    _patch_favicon(static_dir, icon_dir)
    _patch_index_html(static_dir, icon_dir)


def _patch_favicon(static_dir: Path, icon_dir: Path) -> None:
    src = icon_dir / "favicon-256.png"
    dst = static_dir / "favicon.png"
    if not src.exists() or not dst.exists():
        return
    try:
        new_bytes = src.read_bytes()
        if dst.read_bytes() != new_bytes:
            dst.write_bytes(new_bytes)
    except Exception as exc:  # noqa: BLE001
        logger.warning("覆寫 Streamlit favicon.png 失敗：%s", exc)


def _patch_index_html(static_dir: Path, icon_dir: Path) -> None:
    index_path = static_dir / "index.html"
    apple_icon_path = icon_dir / "apple-touch-icon.png"
    if not index_path.exists() or not apple_icon_path.exists():
        return

    try:
        html = index_path.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("讀取 Streamlit index.html 失敗：%s", exc)
        return

    if _MARKER in html:
        return  # 已經修補過

    try:
        apple_b64 = base64.b64encode(apple_icon_path.read_bytes()).decode("ascii")
        injected = (
            f'{_MARKER}\n'
            f'    <link rel="apple-touch-icon" href="data:image/png;base64,{apple_b64}" />\n'
            f'    <title>台股投資分析 PDF 報告產生器</title>\n'
            f"  </head>"
        )
        # Streamlit 原始檔案裡有一個 <title>Streamlit</title>，一併換成我們的標題，
        # 這樣「加入主畫面」預設抓到的捷徑名稱也會是正確的，而不是「Streamlit」。
        if "<title>Streamlit</title>" in html:
            html = html.replace("<title>Streamlit</title>", "")
        new_html = html.replace("</head>", injected, 1)
        if new_html == html:
            return  # 找不到 </head>，格式跟預期不同，放棄修補以免寫壞檔案
        index_path.write_text(new_html, encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        logger.warning("修補 Streamlit index.html 失敗：%s", exc)
