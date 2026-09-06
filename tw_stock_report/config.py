"""專案共用設定值。"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CACHE_DIR = PROJECT_ROOT / "cache"

REPORTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# 一般公開頁面用的 User-Agent，識別為一般瀏覽器請求，非用於繞過封鎖。
HTTP_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "TWStockReportBot/1.0 (+personal research tool; contact via project owner)"
)
HTTP_TIMEOUT_SECONDS = 10
HTTP_MAX_RETRIES = 2
HTTP_RETRY_BACKOFF_SECONDS = 1.5
# 對同一網站發出連續請求之間的最小間隔秒數（禮貌性延遲）。
HTTP_MIN_DELAY_SECONDS = 1.0

FINMIND_BASE_URL = "https://api.finmindtrade.com/api/v4/data"
FINMIND_TOKEN = os.environ.get("FINMIND_TOKEN", "").strip() or None

TWSE_OPENAPI_BASE = "https://openapi.twse.com.tw/v1"
MOPS_BASE = "https://mopsov.twse.com.tw/mops/web"

# 快取存活時間（秒）
CACHE_TTL_STOCK_INFO = 24 * 3600
CACHE_TTL_PRICE = 4 * 3600
# 月營收/EPS/財報明細/資產負債表/現金流量表原本用 12 小時 TTL，是針對「單檔
# 互動查詢」調的（同一天內查兩次同一檔不用重打）。「篩選器APP」新增的每日
# 排程批次（scripts/prefetch_fundamentals.py，見該專案 DEVELOPMENT_LOG）一天
# 要對 150 檔都查一次，12 小時 TTL 在每天固定時間跑的排程下等於「每天都是
# cache miss」，150 檔 × 5 個 FinMind 資料集会在單次批次內就把 FinMind
# 匿名額度用完（實測：跑到約 40 檔之後開始出現 402 Payment Required）。
# 這幾個資料集本來就只有月/季更新頻率，拉長 TTL 沒有犧牲時效性，卻能讓
# 排程只在資料真的更新的那幾天需要重新打 FinMind，大幅降低額度消耗。
CACHE_TTL_REVENUE = 7 * 24 * 3600
CACHE_TTL_EPS = 30 * 24 * 3600
CACHE_TTL_NEWS = 2 * 3600

NEWS_MIN_ITEMS_BEFORE_INDUSTRY_FALLBACK = 3
NEWS_INDUSTRY_FALLBACK_DAYS = 30
NEWS_MAX_ITEMS_PER_PROVIDER = 8

DISCLAIMER_TEXT = (
    "所有投資相關內容僅供參考，不構成任何投資建議，使用者應自行評估風險。"
)
NO_RATING_DATA_TEXT = "查無一致公開資料，僅整理公開可得資訊"
