"""Streamlit 網頁介面：輸入股票代號/名稱，產生並下載 PDF 報告。

執行方式：py -m streamlit run tw_stock_report/app_streamlit.py

密碼保護：部署到公開網路（如 Streamlit Community Cloud）時，在該平台的 Secrets
設定中加入 APP_PASSWORD = "你的密碼"，即會啟用簡易密碼保護；本機開發若未設定
APP_PASSWORD（環境變數或 .streamlit/secrets.toml 皆可），則不會要求輸入密碼。
"""
from __future__ import annotations

import base64
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
st.caption("輸入台股代號或名稱，彙整公開資料並產出中文 PDF 投資分析報告。可重複查詢，不需要重新整理或重啟頁面。")

if "report_result" not in st.session_state:
    st.session_state["report_result"] = None  # 上一次成功產生的 ReportResult
if "report_error" not in st.session_state:
    st.session_state["report_error"] = None

stock_input = st.text_input("股票代號或名稱", placeholder="例如：2330 或 台積電")
generate_clicked = st.button("產生報告", type="primary", disabled=not stock_input.strip())

if generate_clicked:
    # 先清掉舊結果，避免產生失敗時畫面還殘留上一次的報告，讓人誤以為是這次的結果
    st.session_state["report_result"] = None
    st.session_state["report_error"] = None
    with st.spinner("彙整公開資料並產生報告中，可能需要一些時間..."):
        try:
            st.session_state["report_result"] = generate_report(stock_input.strip())
        except IdentityNotFound as exc:
            st.session_state["report_error"] = str(exc)

if st.session_state["report_error"]:
    st.error(st.session_state["report_error"])

result = st.session_state["report_result"]
if result is not None:
    st.success(f"報告已產生：{result.data.identity.company_name}（{result.data.identity.stock_id}）")

    # 用 st.session_state 保存結果，是因為下載按鈕本身點擊也會觸發整頁重新執行；
    # 若結果只存在區域變數裡，下載當下這個結果就會消失，畫面看起來像「重置」了，
    # 誤以為要重新整理/重啟才能再查下一檔。存進 session_state 後，這裡的內容就能
    # 在任何後續互動（含下載按鈕本身）之後繼續顯示，可以直接在上方輸入新代號再查一次。
    pdf_filename = f"{result.data.identity.stock_id}_{result.data.identity.company_name}.pdf"

    col_open, col_download = st.columns(2)
    with col_open:
        # 用 st.link_button（會以新分頁開啟）而非直接觸發下載，是因為 iOS Safari
        # 對「下載」型連結常常不會真的存檔，而是用 Quick Look 全螢幕預覽把目前
        # 這個分頁整個蓋掉，使用者會找不到路回到查詢畫面。開新分頁的話，原本這個
        # 查詢頁面會完整保留在背後（或分頁列表中），切換回來就能繼續查下一檔。
        pdf_base64 = base64.b64encode(result.pdf_bytes).decode("ascii")
        st.link_button(
            "🌐 用瀏覽器開啟（新分頁）",
            url=f"data:application/pdf;base64,{pdf_base64}",
            use_container_width=True,
        )
    with col_download:
        st.download_button(
            "📥 下載 PDF 到裝置",
            data=result.pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            use_container_width=True,
        )
    st.caption(
        "手機（尤其 iPhone）建議用「用瀏覽器開啟」：會在新分頁顯示 PDF，這個查詢頁面不會不見，"
        "看完切換回這個分頁即可繼續查下一檔。「下載」則是把檔案直接存到裝置裡。"
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
