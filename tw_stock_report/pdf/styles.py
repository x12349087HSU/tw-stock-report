"""報告共用的段落與表格樣式。"""
from __future__ import annotations

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle, StyleSheet1
from reportlab.lib.units import cm
from reportlab.platypus import TableStyle

from .fonts import register_cjk_fonts

COLOR_BRAND = colors.HexColor("#1f4e8c")
COLOR_BRAND_LIGHT = colors.HexColor("#eaf0fa")
COLOR_ACCENT = colors.HexColor("#c0521f")
COLOR_ACCENT_LIGHT = colors.HexColor("#fbe9df")
COLOR_TEXT = colors.HexColor("#1a1a1a")
COLOR_MUTED = colors.HexColor("#666666")
COLOR_WARN_BG = colors.HexColor("#fff6e5")
COLOR_TABLE_ALT = colors.HexColor("#f5f7fa")
COLOR_PASS = colors.HexColor("#1a7a3c")
COLOR_PASS_BG = colors.HexColor("#e9f7ee")
COLOR_FAIL = colors.HexColor("#a33")
COLOR_FAIL_BG = colors.HexColor("#fdecec")
COLOR_UNKNOWN = colors.HexColor("#8a6d00")
COLOR_UNKNOWN_BG = colors.HexColor("#fbf3d9")


def build_stylesheet() -> StyleSheet1:
    regular, bold = register_cjk_fonts()

    styles = StyleSheet1()
    styles.add(ParagraphStyle("ReportTitle", fontName=bold, fontSize=20, leading=26, textColor=COLOR_BRAND, alignment=TA_LEFT, spaceAfter=4))
    styles.add(ParagraphStyle("ReportSubtitle", fontName=regular, fontSize=10, leading=14, textColor=COLOR_MUTED, spaceAfter=14))
    styles.add(ParagraphStyle("SectionHeading", fontName=bold, fontSize=13.5, leading=18, textColor=colors.white, spaceBefore=14, spaceAfter=8))
    styles.add(ParagraphStyle("SubHeading", fontName=bold, fontSize=10.5, leading=14, textColor=COLOR_BRAND, spaceBefore=8, spaceAfter=4))
    styles.add(ParagraphStyle("Body", fontName=regular, fontSize=9.5, leading=14.5, textColor=COLOR_TEXT, spaceAfter=6))
    styles.add(ParagraphStyle("BodyCentered", parent=styles["Body"], alignment=TA_CENTER))
    styles.add(ParagraphStyle("Caption", fontName=regular, fontSize=8, leading=11, textColor=COLOR_MUTED, spaceAfter=10))
    styles.add(ParagraphStyle("NewsTitle", fontName=bold, fontSize=9.5, leading=13, textColor=COLOR_TEXT, spaceAfter=1))
    styles.add(ParagraphStyle("NewsMeta", fontName=regular, fontSize=8, leading=11, textColor=COLOR_MUTED, spaceAfter=1))
    styles.add(ParagraphStyle("NewsSnippet", fontName=regular, fontSize=8.8, leading=12.5, textColor=COLOR_TEXT, spaceAfter=8))
    styles.add(ParagraphStyle("Disclaimer", fontName=bold, fontSize=9, leading=13, textColor=colors.HexColor("#8a5a00"), alignment=TA_CENTER))
    styles.add(ParagraphStyle("SourceStatusOk", fontName=regular, fontSize=8, leading=11, textColor=colors.HexColor("#1a7a3c")))
    styles.add(ParagraphStyle("SourceStatusFail", fontName=regular, fontSize=8, leading=11, textColor=colors.HexColor("#a33"), ))
    styles.add(ParagraphStyle("TierHeading", fontName=bold, fontSize=10.5, leading=14, textColor=COLOR_TEXT, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle("ChecklistItemName", fontName=bold, fontSize=8.8, leading=12, textColor=COLOR_TEXT))
    styles.add(ParagraphStyle("ChecklistDetail", fontName=regular, fontSize=8.3, leading=11.5, textColor=COLOR_MUTED))
    styles.add(ParagraphStyle("ChecklistPass", fontName=bold, fontSize=9, leading=12, textColor=COLOR_PASS, alignment=TA_CENTER))
    styles.add(ParagraphStyle("ChecklistFail", fontName=bold, fontSize=9, leading=12, textColor=COLOR_FAIL, alignment=TA_CENTER))
    styles.add(ParagraphStyle("ChecklistUnknown", fontName=bold, fontSize=9, leading=12, textColor=COLOR_UNKNOWN, alignment=TA_CENTER))
    return styles


def basic_info_table_style() -> TableStyle:
    return TableStyle(
        [
            ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),  # 呼叫端會覆蓋成 CJK 字型名稱
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("BACKGROUND", (0, 0), (0, -1), COLOR_BRAND_LIGHT),
            ("TEXTCOLOR", (0, 0), (0, -1), COLOR_BRAND),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def rating_table_style() -> TableStyle:
    return TableStyle(
        [
            ("FONTSIZE", (0, 0), (-1, -1), 8.5),
            ("BACKGROUND", (0, 0), (-1, 0), COLOR_ACCENT),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, COLOR_ACCENT_LIGHT]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0b299")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
    )
