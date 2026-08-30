"""Streamlit 網頁介面：輸入股票代號/名稱，產生並下載 PDF 報告。

執行方式：py -m streamlit run tw_stock_report/app_streamlit.py

密碼保護：部署到公開網路（如 Streamlit Community Cloud）時，在該平台的 Secrets
設定中加入 APP_PASSWORD = "你的密碼"，即會啟用簡易密碼保護；本機開發若未設定
APP_PASSWORD（環境變數或 .streamlit/secrets.toml 皆可），則不會要求輸入密碼。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Streamlit Community Cloud 執行時不會像本機 `python -m streamlit run` 一樣把
# 專案根目錄（tw_stock_report/ 的上一層）放進 sys.path，導致 `import tw_stock_report.*`
# 失敗（ModuleNotFoundError）。這裡明確把根目錄加入 sys.path，確保任何執行方式都能正確匯入。
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st

from tw_stock_report.identity import IdentityNotFound
from tw_stock_report.report import generate_report

st.set_page_config(page_title="台股投資分析 PDF 報告產生器", page_icon="📈")


def _get_configured_password() -> str | None:
    try:
        secret_pwd = st.secrets.get("APP_PASSWORD")
    except Exception:
        secret_pwd = None
    return secret_pwd or os.environ.get("APP_PASSWORD") or None


def _require_password() -> bool:
    """回傳是否已通過密碼驗證（或本來就不需要密碼）。"""
    correct_password = _get_configured_password()
    if not correct_password:
        return True
    if st.session_state.get("authenticated"):
        return True

    st.title("台股投資分析 PDF 報告產生器")
    st.info("此服務已啟用密碼保護，請輸入密碼後繼續。")
    entered = st.text_input("密碼", type="password")
    if st.button("登入"):
        if entered == correct_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("密碼錯誤，請再試一次。")
    return False


if not _require_password():
    st.stop()

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
