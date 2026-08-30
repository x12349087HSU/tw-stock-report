"""用 ReportLab Platypus 組出完整的中文投資分析 PDF 報告。"""
from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .. import config
from ..charts.eps_chart import render_eps_chart
from ..charts.price_chart import render_price_chart
from ..charts.revenue_chart import render_revenue_chart
from ..models import ChecklistItem, ReportData
from .fonts import register_cjk_fonts
from .styles import (
    COLOR_ACCENT,
    COLOR_BRAND,
    COLOR_FAIL_BG,
    COLOR_PASS_BG,
    COLOR_TABLE_ALT,
    COLOR_UNKNOWN_BG,
    COLOR_WARN_BG,
    basic_info_table_style,
    build_stylesheet,
    rating_table_style,
)

PAGE_WIDTH, _ = A4
CONTENT_WIDTH = PAGE_WIDTH - 2 * 1.8 * cm


def _section_heading(styles, text: str) -> Table:
    """區塊標題：用單一儲存格的表格畫出品牌色底色的橫幅，相容性比 Paragraph.backColor 更穩定。"""
    p = Paragraph(text, styles["SectionHeading"])
    t = Table([[p]], colWidths=[CONTENT_WIDTH])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_BRAND),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _fallback_box(styles, text: str) -> Table:
    p = Paragraph(text, styles["Body"])
    t = Table([[p]], colWidths=[CONTENT_WIDTH])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), COLOR_WARN_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#e0c070")),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    return t


def _image_flowable(png_bytes: bytes, max_width: float) -> Image:
    img = Image(io.BytesIO(png_bytes))
    scale = max_width / img.imageWidth
    img.drawWidth = max_width
    img.drawHeight = img.imageHeight * scale
    return img


def _build_basic_info_section(styles, data: ReportData) -> list:
    ident = data.identity
    rows = [
        ["公司名稱", ident.company_name],
        ["股票代號", ident.stock_id],
        ["產業分類", ident.industry_name],
        ["市場別", ident.market_type],
        ["報告產出日期", data.generated_at.isoformat()],
    ]
    regular, bold = register_cjk_fonts()
    table = Table(rows, colWidths=[3.5 * cm, CONTENT_WIDTH - 3.5 * cm])
    style = basic_info_table_style()
    style.add("FONTNAME", (0, 0), (-1, -1), regular)
    style.add("FONTNAME", (0, 0), (0, -1), bold)
    table.setStyle(style)
    return [_section_heading(styles, "一、個股基本資訊"), Spacer(1, 6), table, Spacer(1, 10)]


def _build_price_section(styles, data: ReportData) -> list:
    flow: list = [_section_heading(styles, "二、股價走勢分析"), Spacer(1, 6)]
    bars = data.price_bars_1y
    if not bars:
        flow.append(
            _fallback_box(styles, "股價資料暫時無法取得（FinMind 與官方備援皆失敗），此區塊略過。")
        )
        flow.append(Spacer(1, 10))
        return flow

    periods = [(3, "近 3 個月收盤價與成交量"), (6, "近 6 個月收盤價與成交量"), (12, "近 1 年收盤價與成交量")]
    for months, title in periods:
        try:
            png = render_price_chart(bars, months, title)
            flow.append(_image_flowable(png, CONTENT_WIDTH))
            flow.append(Spacer(1, 6))
        except ValueError:
            flow.append(Paragraph(f"{title}：資料不足，略過此圖。", styles["Caption"]))

    if data.price_high_1y and data.price_low_1y:
        flow.append(
            Paragraph(
                f"近一年區間高點 {data.price_high_1y.high:,.1f} 元"
                f"（{data.price_high_1y.trade_date.isoformat()}）、"
                f"低點 {data.price_low_1y.low:,.1f} 元"
                f"（{data.price_low_1y.trade_date.isoformat()}）。",
                styles["Body"],
            )
        )
    flow.append(Spacer(1, 10))
    return flow


def _build_revenue_section(styles, data: ReportData) -> list:
    flow: list = [_section_heading(styles, "三、近兩年營收分析"), Spacer(1, 6)]
    rows = data.revenue_rows_24m
    if not rows:
        flow.append(_fallback_box(styles, "月營收資料暫時無法取得（FinMind 與官方備援皆失敗），此區塊略過。"))
        flow.append(Spacer(1, 10))
        return flow

    try:
        png = render_revenue_chart(rows)
        flow.append(_image_flowable(png, CONTENT_WIDTH))
        flow.append(Spacer(1, 6))
    except ValueError:
        flow.append(Paragraph("營收資料不足，無法繪製圖表。", styles["Caption"]))

    if data.revenue_summary_text:
        flow.append(Paragraph(data.revenue_summary_text, styles["Body"]))
    flow.append(Spacer(1, 10))
    return flow


def _build_eps_section(styles, data: ReportData) -> list:
    flow: list = [_section_heading(styles, "四、EPS 分析"), Spacer(1, 6)]
    quarterly = data.eps_rows_8q
    if not quarterly:
        flow.append(_fallback_box(styles, "EPS 資料暫時無法取得（FinMind 與官方備援皆失敗），此區塊略過。"))
        flow.append(Spacer(1, 10))
        return flow

    try:
        png = render_eps_chart(quarterly)
        flow.append(_image_flowable(png, CONTENT_WIDTH))
        flow.append(Spacer(1, 6))
    except ValueError:
        flow.append(Paragraph("EPS 資料不足，無法繪製圖表。", styles["Caption"]))

    if data.eps_rows_annual:
        regular, bold = register_cjk_fonts()
        header = ["年度", *[str(r.year) for r in data.eps_rows_annual]]
        values = ["年度 EPS（元）", *[f"{r.eps:.2f}" for r in data.eps_rows_annual]]
        table = Table([header, values], colWidths=None)
        table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, -1), regular),
                    ("FONTNAME", (0, 0), (0, -1), bold),
                    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                    ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_ALT),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                    ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        flow.append(table)
        flow.append(Spacer(1, 6))

    if data.eps_summary_text:
        flow.append(Paragraph(data.eps_summary_text, styles["Body"]))
    flow.append(Spacer(1, 10))
    return flow


def _news_item_flowable(styles, item) -> list:
    date_str = item.publish_date.isoformat() if item.publish_date else "日期未知"
    flow = [
        Paragraph(item.title, styles["NewsTitle"]),
        Paragraph(f"{date_str}　來源：{item.source}", styles["NewsMeta"]),
    ]
    if item.snippet:
        flow.append(Paragraph(item.snippet, styles["NewsSnippet"]))
    if item.url:
        flow.append(Paragraph(f'<link href="{item.url}" color="#1f4e8c">{item.url}</link>', styles["NewsMeta"]))
    flow.append(Spacer(1, 6))
    return flow


def _build_news_section(styles, data: ReportData) -> list:
    flow: list = [_section_heading(styles, "五、新聞與研究摘要"), Spacer(1, 6)]

    flow.append(Paragraph("產業走向", styles["SubHeading"]))
    flow.append(
        Paragraph(data.industry_trend_text or "查無足夠公開資料可整理產業走向摘要。", styles["Body"])
    )

    flow.append(Paragraph("個股分析重點", styles["SubHeading"]))
    flow.append(
        Paragraph(data.stock_highlight_text or "查無足夠公開資料可整理個股分析重點。", styles["Body"])
    )

    flow.append(Paragraph("近期新聞摘要", styles["SubHeading"]))
    all_news = [*data.stock_news, *data.industry_news]
    if not all_news:
        flow.append(_fallback_box(styles, "新聞模組所有來源皆查無資料或無法存取，此區塊暫無內容可顯示。"))
    else:
        for item in all_news[:12]:
            flow.extend(_news_item_flowable(styles, item))
    flow.append(Spacer(1, 6))
    return flow


def _build_rating_section(styles, data: ReportData) -> list:
    flow: list = [_section_heading(styles, "六、目標價與投資評等"), Spacer(1, 6)]
    if not data.ratings:
        flow.append(_fallback_box(styles, config.NO_RATING_DATA_TEXT))
        flow.append(Spacer(1, 10))
        return flow

    header = ["日期", "法人/來源", "評等", "目標價", "備註"]
    rows = [header]
    for r in data.ratings[:15]:
        rows.append(
            [
                r.publish_date.isoformat() if r.publish_date else "-",
                r.institution or "未辨識",
                r.rating or "未辨識",
                f"{r.target_price:.1f}" if r.target_price is not None else "-",
                r.note or "",
            ]
        )
    regular, bold = register_cjk_fonts()
    table = Table(rows, colWidths=[2.1 * cm, 3.2 * cm, 2.2 * cm, 2.2 * cm, CONTENT_WIDTH - 9.7 * cm])
    style = rating_table_style()
    style.add("FONTNAME", (0, 0), (-1, -1), regular)
    style.add("FONTNAME", (0, 0), (-1, 0), bold)
    table.setStyle(style)
    flow.append(table)
    flow.append(Spacer(1, 6))
    flow.append(
        Paragraph(
            "以上為公開新聞中整理之目標價/評等資訊，非官方研究報告全文，僅供參考，實際內容請以原始新聞連結為準。",
            styles["Caption"],
        )
    )
    flow.append(Spacer(1, 10))
    return flow


def _checklist_result_cell(styles, item: ChecklistItem) -> Paragraph:
    if item.passed is True:
        return Paragraph("通過", styles["ChecklistPass"])
    if item.passed is False:
        return Paragraph("未通過", styles["ChecklistFail"])
    return Paragraph("資料不足", styles["ChecklistUnknown"])


def _build_checklist_section(styles, data: ReportData) -> list:
    flow: list = [_section_heading(styles, "七、核心成長動能基本面自檢表"), Spacer(1, 6)]
    items = data.checklist_items
    if not items:
        flow.append(_fallback_box(styles, "季度財報資料暫時無法取得（FinMind 財報/資產負債表/現金流量表皆失敗），此區塊略過。"))
        flow.append(Spacer(1, 10))
        return flow

    passed_count = sum(1 for i in items if i.passed is True)
    failed_count = sum(1 for i in items if i.passed is False)
    unknown_count = sum(1 for i in items if i.passed is None)
    flow.append(
        Paragraph(
            f"共 {len(items)} 項指標：通過 {passed_count} 項、未通過 {failed_count} 項、資料不足 {unknown_count} 項。",
            styles["Body"],
        )
    )
    flow.append(
        Paragraph(
            "以下指標之公式與門檻依常見財務分析慣例訂定（如 ROE/ROA 採近 8 季 TTM、"
            "現金轉換率＝營業現金流／稅後淨利、利息保障倍數＝(稅前淨利＋利息費用)／利息費用），"
            "各項判定依據已列於「說明」欄，非官方或單一標準公式，僅供參考。",
            styles["Caption"],
        )
    )

    regular, bold = register_cjk_fonts()
    tiers_seen: list[int] = []
    for item in items:
        if item.tier not in tiers_seen:
            tiers_seen.append(item.tier)

    for tier in tiers_seen:
        tier_items = [i for i in items if i.tier == tier]
        flow.append(Paragraph(tier_items[0].tier_name, styles["TierHeading"]))

        rows = [["項目", "結果", "說明"]]
        row_colors = [COLOR_TABLE_ALT]
        for item in tier_items:
            rows.append(
                [
                    Paragraph(item.name, styles["ChecklistItemName"]),
                    _checklist_result_cell(styles, item),
                    Paragraph(item.detail, styles["ChecklistDetail"]),
                ]
            )
            if item.passed is True:
                row_colors.append(COLOR_PASS_BG)
            elif item.passed is False:
                row_colors.append(COLOR_FAIL_BG)
            else:
                row_colors.append(COLOR_UNKNOWN_BG)

        table = Table(rows, colWidths=[5.2 * cm, 2.6 * cm, CONTENT_WIDTH - 7.8 * cm])
        style = TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), regular),
                ("FONTNAME", (0, 0), (-1, 0), bold),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("BACKGROUND", (0, 0), (-1, 0), COLOR_TABLE_ALT),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
        for row_idx, bg in enumerate(row_colors):
            style.add("BACKGROUND", (0, row_idx), (-1, row_idx), bg)
        table.setStyle(style)
        flow.append(table)
        flow.append(Spacer(1, 8))

    flow.append(Spacer(1, 2))
    return flow


def _build_disclaimer_section(styles) -> list:
    t = Table([[Paragraph(config.DISCLAIMER_TEXT, styles["Disclaimer"])]], colWidths=[CONTENT_WIDTH])
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#fff3cd")),
                ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#e0b200")),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return [Spacer(1, 12), t]


def _build_source_status_section(styles, data: ReportData) -> list:
    if not data.source_statuses:
        return []
    flow: list = [Spacer(1, 14), Paragraph("附註：資料來源狀態", styles["SubHeading"])]
    for s in data.source_statuses:
        style_name = "SourceStatusOk" if s.ok else "SourceStatusFail"
        mark = "OK" if s.ok else "！"
        text = f"[{mark}] {s.module}：{s.source_used}"
        if s.message:
            text += f"（{s.message}）"
        flow.append(Paragraph(text, styles[style_name]))
    return flow


def build_pdf(data: ReportData) -> bytes:
    """組出完整 PDF，回傳 bytes。任何單一區塊的資料缺漏都已在各 _build_* 函式內以
    fallback 文字處理過，這裡只負責排版組裝，不應該再因為資料問題而失敗。"""
    styles = build_stylesheet()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=1.8 * cm,
        rightMargin=1.8 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.6 * cm,
        title=f"{data.identity.company_name}（{data.identity.stock_id}）投資分析報告",
    )

    story: list = []
    story.append(Paragraph(f"{data.identity.company_name}（{data.identity.stock_id}）投資分析報告", styles["ReportTitle"]))
    story.append(
        Paragraph(
            f"{data.identity.market_type}．{data.identity.industry_name}　|　報告產出日期：{data.generated_at.isoformat()}",
            styles["ReportSubtitle"],
        )
    )

    story.extend(_build_basic_info_section(styles, data))
    story.extend(_build_price_section(styles, data))
    story.extend(_build_revenue_section(styles, data))
    story.extend(_build_eps_section(styles, data))
    story.extend(_build_news_section(styles, data))
    story.extend(_build_rating_section(styles, data))
    story.extend(_build_checklist_section(styles, data))
    story.extend(_build_disclaimer_section(styles))
    story.extend(_build_source_status_section(styles, data))

    doc.build(story)
    return buf.getvalue()
