"""從新聞標題／摘要中以關鍵字＋正規表示式，規則式擷取目標價與評等資訊。

純文字處理，不做任何網路請求；擷取不到就回傳 None，絕不憑空捏造數字。
"""
from __future__ import annotations

import re

from ...models import NewsItem, RatingItem

_TARGET_PRICE_RE = re.compile(r"目標(?:股)?價\D{0,4}([0-9]{1,4}(?:\.[0-9]{1,2})?)\s*元?")
_ALT_TARGET_PRICE_RE = re.compile(r"(?:喊到|上看|喊價)\D{0,2}([0-9]{1,4}(?:\.[0-9]{1,2})?)\s*元")

_RATING_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("買進", re.compile(r"買進|優於大盤|加碼|強力買進")),
    ("增持", re.compile(r"增持")),
    ("中立", re.compile(r"中立|持有|區間操作")),
    ("賣出", re.compile(r"賣出|劣於大盤|減碼")),
]

_INSTITUTIONS = [
    "摩根士丹利", "摩根大通", "高盛", "瑞銀", "瑞士信貸", "花旗", "美銀美林", "巴克萊",
    "德意志銀行", "野村", "里昂證券", "麥格理", "傑富瑞", "貝萊德",
    "元大", "凱基", "群益", "富邦", "國泰", "統一", "兆豐", "永豐", "台新", "第一金",
    "日盛", "康和", "華南永昌", "玉山", "中信", "土銀",
    "外資", "投信", "法人",
]


def _find_institution(text: str) -> str:
    for name in _INSTITUTIONS:
        if name in text:
            return name
    return ""


def _find_rating(text: str) -> str:
    for label, pattern in _RATING_PATTERNS:
        if pattern.search(text):
            return label
    return ""


def _find_target_price(text: str) -> float | None:
    for pattern in (_TARGET_PRICE_RE, _ALT_TARGET_PRICE_RE):
        m = pattern.search(text)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                continue
    return None


def extract_rating(item: NewsItem) -> RatingItem | None:
    """從單則新聞中擷取評等資訊。標題+摘要中都沒有目標價也沒有評等關鍵字時回傳 None。"""
    text = f"{item.title} {item.snippet}"
    target_price = _find_target_price(text)
    rating = _find_rating(text)
    institution = _find_institution(text)

    if target_price is None and not rating:
        return None

    return RatingItem(
        source_title=item.title,
        source_url=item.url,
        publish_date=item.publish_date,
        institution=institution,
        rating=rating,
        target_price=target_price,
        note=item.source,
    )
