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
CACHE_TTL_REVENUE = 12 * 3600
CACHE_TTL_EPS = 12 * 3600
CACHE_TTL_NEWS = 2 * 3600

NEWS_MIN_ITEMS_BEFORE_INDUSTRY_FALLBACK = 3
NEWS_INDUSTRY_FALLBACK_DAYS = 30
NEWS_MAX_ITEMS_PER_PROVIDER = 8

DISCLAIMER_TEXT = (
    "所有投資相關內容僅供參考，不構成任何投資建議，使用者應自行評估風險。"
)
NO_RATING_DATA_TEXT = "查無一致公開資料，僅整理公開可得資訊"
