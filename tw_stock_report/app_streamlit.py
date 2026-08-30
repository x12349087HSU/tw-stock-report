"""Streamlit 網頁介面：輸入股票代號/名稱，產生並下載 PDF 報告。

執行方式：py -m streamlit run tw_stock_report/app_streamlit.py

密碼保護：部署到公開網路（如 Streamlit Community Cloud）時，在該平台的 Secrets
設定中加入 APP_PASSWORD = "你的密碼"，即會啟用簡易密碼保護；本機開發若未設定
APP_PASSWORD（環境變數或 .streamlit/secrets.toml 皆可），則不會要求輸入密碼。
"""
from __future__ import annotations

import base64
import json
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
import streamlit.components.v1 as components

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
    pdf_base64 = base64.b64encode(result.pdf_bytes).decode("ascii")

    # 「用瀏覽器開啟」與「分享」都改用 Blob URL（瀏覽器端用 JS 把 base64 轉成檔案，
    # 再用 URL.createObjectURL 產生 blob: 網址），而不是直接把 data: URI 拿去
    # window.open() 或 <a download>。原因：
    #   - data: URI 若拿去做「開新分頁導覽」，會被 Chrome/Safari 的防釣魚機制擋下
    #     （視為可疑的網址列偽裝手法），結果就是先前回報的「開新分頁後空白」。
    #   - <a download> 在 iPhone Safari 上常常不會真的觸發存檔，而是改用系統層級
    #     的 Quick Look 全螢幕預覽把目前畫面整個蓋掉；如果是從「加入主畫面」的
    #     捷徑開啟，關閉 Quick Look 後有時甚至無法回到原本的頁面，只能重開 App。
    #   - blob: 網址是瀏覽器原生、專門設計給「這頁動態產生的檔案」使用的機制，
    #     用 window.open() 開啟走的是正常瀏覽器分頁／原生 PDF 檢視器，不會觸發
    #     上述兩種問題，分頁裡也會有瀏覽器自己的下載/列印功能可以之後再存檔。
    components.html(
        f"""
        <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
          display:flex; gap:0.5em; flex-wrap:wrap;">
          <button id="openBtn" style="flex:1; min-width:140px; padding:0.5em 1em; font-size:1em;
            border-radius:8px; border:none; background:#ff4b4b; color:#fff;
            cursor:pointer;">📄 用瀏覽器開啟 PDF</button>
          <button id="shareBtn" style="flex:1; min-width:140px; padding:0.5em 1em; font-size:1em;
            border-radius:8px; border:1px solid rgba(49,51,63,0.2); background:#fff;
            cursor:pointer;">📤 選擇開啟方式（分享）</button>
        </div>
        <div id="actionMsg" style="margin-top:0.4em; font-size:0.85em; color:#666;"></div>
        <script>
        const b64Data = {json.dumps(pdf_base64)};
        const fileName = {json.dumps(pdf_filename)};

        function b64ToBlob(b64, contentType) {{
          const byteChars = atob(b64);
          const byteNumbers = new Array(byteChars.length);
          for (let i = 0; i < byteChars.length; i++) {{
            byteNumbers[i] = byteChars.charCodeAt(i);
          }}
          return new Blob([new Uint8Array(byteNumbers)], {{type: contentType}});
        }}

        const msg = document.getElementById('actionMsg');

        document.getElementById('openBtn').addEventListener('click', () => {{
          msg.innerText = '';
          try {{
            const blob = b64ToBlob(b64Data, 'application/pdf');
            const blobUrl = URL.createObjectURL(blob);
            const opened = window.open(blobUrl, '_blank');
            if (!opened) {{
              msg.innerText = '瀏覽器擋下了開啟視窗，請改用下方「下載 PDF 到裝置」按鈕。';
            }}
          }} catch (err) {{
            msg.innerText = '開啟失敗，請改用下方「下載 PDF 到裝置」按鈕。';
          }}
        }});

        document.getElementById('shareBtn').addEventListener('click', async () => {{
          msg.innerText = '';
          try {{
            const blob = b64ToBlob(b64Data, 'application/pdf');
            const file = new File([blob], fileName, {{type: 'application/pdf'}});
            if (navigator.canShare && navigator.canShare({{files: [file]}})) {{
              await navigator.share({{files: [file], title: fileName}});
            }} else {{
              msg.innerText = '此瀏覽器不支援分享功能，請改用「用瀏覽器開啟」或「下載」。';
            }}
          }} catch (err) {{
            if (err && err.name !== 'AbortError') {{
              msg.innerText = '分享失敗，請改用「用瀏覽器開啟」或「下載」。';
            }}
          }}
        }});
        </script>
        """,
        height=90,
    )

    st.download_button(
        "📥 下載 PDF 到裝置",
        data=result.pdf_bytes,
        file_name=pdf_filename,
        mime="application/pdf",
        use_container_width=True,
    )
    st.caption(
        "建議先用「用瀏覽器開啟 PDF」查看：會在新分頁用瀏覽器內建的 PDF 檢視器開啟，"
        "裡面本身就有下載／列印功能，看完直接切換回這個分頁即可繼續查下一檔。"
    )

    st.subheader("PDF 預覽")
    st.caption("下方為報告內嵌預覽（在本頁面內顯示，不會離開這個查詢頁）；若空白請改用上方按鈕。")
    st.markdown(
        f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="600"'
        f' style="border:1px solid #d0d0d0;border-radius:6px;"></iframe>',
        unsafe_allow_html=True,
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
