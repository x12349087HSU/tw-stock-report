"""Streamlit 網頁介面：輸入股票代號/名稱，產生並下載 PDF 報告。

執行方式：py -m streamlit run tw_stock_report/app_streamlit.py
"""
from __future__ import annotations

import streamlit as st

from tw_stock_report.identity import IdentityNotFound
from tw_stock_report.report import generate_report

st.set_page_config(page_title="台股投資分析 PDF 報告產生器", page_icon="📈")

st.title("台股投資分析 PDF 報告產生器")
st.caption("輸入台股代號或名稱，彙整公開資料並產出中文 PDF 投資分析報告。")

stock_input = st.text_input("股票代號或名稱", placeholder="例如：2330 或 台積電")
generate_clicked = st.button("產生報告", type="primary", disabled=not stock_input.strip())

if generate_clicked:
    with st.spinner("彙整公開資料並產生報告中，可能需要一些時間..."):
        try:
            result = generate_report(stock_input.strip())
        except IdentityNotFound as exc:
            st.error(str(exc))
        else:
            st.success(f"報告已產生：{result.data.identity.company_name}（{result.data.identity.stock_id}）")

            st.download_button(
                "下載 PDF 報告",
                data=result.pdf_bytes,
                file_name=f"{result.data.identity.stock_id}_{result.data.identity.company_name}.pdf",
                mime="application/pdf",
            )

            st.subheader("資料來源狀態")
            for status in result.data.source_statuses:
                label = f"{status.module}：{status.source_used}"
                if status.ok:
                    st.success(label + (f"（{status.message}）" if status.message else ""))
                else:
                    st.warning(label + (f"（{status.message}）" if status.message else ""))

st.divider()
st.caption("所有投資相關內容僅供參考，不構成任何投資建議，使用者應自行評估風險。")
