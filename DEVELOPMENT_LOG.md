# 開發紀錄

這份文件記錄專案從 0 到目前狀態的關鍵決策、踩過的坑、以及已知限制。
目的是讓之後不管是你自己還是協助開發的人（包含未來的 Claude 對話），
不用重新踩一次已經踩過的坑，也知道某些「看起來怪怪的」寫法背後的原因。

一般的「怎麼安裝、怎麼用」請看 [README.md](README.md)；這份文件是給
「要改程式碼的人」看的。

---

## 1. 整體架構

```
tw_stock_report/
├── identity.py              股票代號/名稱 -> StockIdentity（唯一允許查無資料時 raise 的模組）
├── providers/                所有對外部資料源的存取，統一回傳 ProviderResult，絕不對外拋例外
│   ├── price.py / revenue.py / eps.py     FinMind 主要 + 官方來源備援
│   ├── fundamentals.py / balance_sheet.py / cash_flow.py   季度財報明細，FinMind only
│   ├── news/                 FinMind 個股新聞 + 鉅亨網關鍵字搜尋，多層 fallback
│   └── rating/                目標價/評等，重用 news 的抓取結果做規則式擷取
├── analysis/checklist.py    基本面自檢表（四層核心成長動能）評核引擎
├── charts/                   matplotlib 圖表，皆回傳 PNG bytes
├── pdf/                       ReportLab 組版
├── report.py                  Orchestrator，CLI 和 Streamlit 都只呼叫這裡的 generate_report()
├── cli.py / app_streamlit.py 兩個介面，邏輯共用 report.py
└── assets/                    字型、圖示等靜態資源
```

**核心設計原則**：每個 provider 都不能讓例外往外傳，一律包成 `ProviderResult(ok, data, error)`。
單一資料源掛掉只影響對應的那個 PDF 區塊變成 fallback 提示文字，不會讓整份報告產生失敗。

---

## 2. 資料來源的關鍵決策

### 2.1 為什麼股價/營收/EPS 用 FinMind 為主
FinMind（`api.finmindtrade.com`）是免登入、公開的台股資料聚合 API，涵蓋股價、月營收、
季度財報（含 EPS、資產負債表、現金流量表）。相較於直接刻自己的爬蟲，開發與維護成本
低很多。官方來源（證交所 STOCK_DAY、MOPS）作為備援，只有股價（僅上市）跟營收/EPS
有做，資產負債表/現金流量表/損益表明細目前**只有 FinMind 一層**，沒有備援。

### 2.2 為什麼新聞來源不是一開始規劃的 MoneyDJ / 經濟日報(UDN)
開發過程中實際檢查了各大新聞網站的 `robots.txt`，發現：

- **MoneyDJ、UDN（經濟日報）、Yahoo奇摩股市、中央社、工商時報、中時、自由財經**
  等站台的 robots.txt 都**明確**用 `User-agent: ClaudeBot` / `Claude-Web` / `anthropic-ai`
  搭配 `Disallow: /` 擋掉，部分還附上「禁止用於 AI/LLM 用途」的著作權聲明。
- 只有 **鉅亨網（news.cnyes.com）** 沒有這類限制。

因此新聞模組改用「**鉅亨網關鍵字搜尋 API** + **FinMind 的 TaiwanStockNews 資料集**
（FinMind 自己聚合多家新聞來源後提供的 API，不是我們直接爬那些原始站台，適用 FinMind
自己的服務條款）」。這不是為了規避限制才選的替代方案，而是**優先尊重公開來源的使用限制**
這個原則下唯一走得通的路。

如果之後想再加新聞來源，**務必先查該站的 robots.txt**，看有沒有針對 AI 爬蟲的
Disallow 規則。

### 2.3 鉅亨網搜尋 API 的已知限制
`api.cnyes.com/media/api/v1/search/news?q=...` 的多字關鍵字查詢**不是嚴格 AND**，
實測「台積電 目標價」這種複合關鍵字常常回傳跟台積電完全無關、只是剛好也提到
「目標價」的其他個股新聞。因此 `providers/rating/aggregator.py` 額外加了一層
**相關性過濾**（標題+摘要必須包含公司名稱或代號才留下），不能只依賴查詢字串本身。

### 2.4 目標價/評等資料為什麼常常是空的
鉅亨網搜尋 API 只回傳**標題 + 短摘要**（不是全文），沒有做全文擷取（刻意選擇，避免
抓取受版權保護的完整新聞內容）。這代表規則式擷取（`rating/extractor.py`）能不能命中，
高度取決於目標價數字剛好有沒有出現在那一小段摘要裡——**查無資料是正常、預期中的
結果**，不是程式壞掉，PDF 會顯示固定提示文字而不是報錯。

---

## 3. 踩過的資料品質坑（都已修正，但記錄原因避免以後重踩）

### 3.1 FinMind 現金流量表是「累計數」，損益表是「單季數」
`TaiwanStockCashFlowsStatement` 的數值是**當年度累計**（Q1=Q1、Q2=上半年累計、
Q3=前三季累計、Q4=全年累計），跟 `TaiwanStockFinancialStatements`（Revenue/EPS 等，
已驗證過是**單季**數字）的慣例不一樣。一開始沒發現，直接拿累計值當單季用，導致
「現金轉換率」算成 305% 這種離譜數字。修正方式在 `providers/cash_flow.py`：用
累計值相減換算成單季，邏輯跟 `providers/eps.py` 官方備援換算 MOPS 累計 EPS 是同一招。

**教訓**：拿到一個新的 FinMind 資料集，先實際印出同一年四季的數值，確認是單季還是
累計，不要假設。

### 3.2 ROE/ROA 只用了 5 季而非設計的 8 季
`analysis/checklist.py` 的 `_roe_roa()` 原本先把資料裁成「最後 8 季」才去算移動年化
（TTM），但算 TTM 需要往前抓 3 季當基期，裁切在算 TTM *之前*做，導致前 3 季因為
沒有基期資料變成 None，實際只剩 5 季有效值。修正方式：**先用完整歷史算出 TTM 序列，
最後才取最近 8 個有效值**。

**教訓**：任何「先裁切區間、再算移動平均/移動年化」的邏輯，都要檢查裁切的順序有沒有
不小心把算移動統計量需要的暖身資料一起切掉。

### 3.3 FinMind 股價資料偶爾有單日 close=0 的異常值
實測發現 2317（鴻海）在 2025-07-30 這天 FinMind 回傳 close=0（前一天 171.5、
後一天 178.0，明顯是資料源錯誤，不是真的股價歸零）。這種資料點畫在股價圖或
本益比河流圖上會出現一條插到底又彈回來的假崩盤線。修正方式在
`providers/price.py`：解析階段直接過濾掉 open/high/low/close 為 0 或負值的資料列。

**教訓**：外部資料源不可盡信，尤其是「單日值離兩側鄰居差異巨大」這種模式，畫圖前
最好都過一層合理性檢查（sanity check）。

### 3.4 均線需要「暖身」資料，不能只用顯示區間本身算
5/10/20/60 日均線如果只用「近一年」這個顯示區間的資料去算，區間前面 60 天會因為
沒有足夠的歷史資料而無法算出正確的 60MA。解法：`report.py` 抓股價時抓約 3.3 年
（`months=40`），近一年圖表只是從中「切」出最後 12 個月來顯示，但均線計算是用
完整的延伸序列（`price_bars_extended`）計算，確保顯示區間第一天就有正確數值。

---

## 4. 部署到 Streamlit Community Cloud 的限制與坑

### 4.1 `streamlit run` 的 import 路徑在雲端跟本機不一樣
本機用 `python -m streamlit run tw_stock_report/app_streamlit.py`（`-m` + cwd 在專案
根目錄）時，`import tw_stock_report.xxx` 之所以能運作，是因為 `-m` 執行方式會把
**目前工作目錄**加進 `sys.path`。Streamlit Cloud 的執行方式不是這樣，會導致
`ModuleNotFoundError: No module named 'tw_stock_report'`。**已修正**：
`app_streamlit.py` 開頭明確把專案根目錄加進 `sys.path`，不依賴執行方式。

### 4.2 中文字型不能寫死 Windows 路徑
`pdf/fonts.py` 原本只找 `C:\Windows\Fonts\msjh.ttc` 這類 Windows 專屬路徑，雲端是
Linux 主機找不到。**已修正**：內建 Noto Sans TC 字型檔（`assets/fonts/`，OFL 授權）
當作跨平台備援，找不到系統字型時自動退回用內建的。

### 4.3 Streamlit Cloud 上，`site-packages`（套件安裝目錄）是唯讀的
**曾經嘗試但失敗的做法**：想直接覆寫 Streamlit 套件內建的 `static/index.html`，
在裡面插入 `<link rel="apple-touch-icon">`，讓 iOS「加入主畫面」讀取原始 HTML
時就能抓到自訂圖示。本機測試完全成功，但部署到 Streamlit Cloud 後噴
`PermissionError: [Errno 13] Permission denied`——雲端執行環境的套件安裝目錄
是唯讀的，**這條路走不通，之後不要再嘗試**。已改回用
`st.markdown(unsafe_allow_html=True)` 插入 `<link>` 標籤（渲染在主頁面 DOM 裡，
不需要碰到伺服器檔案），但這個方式仍然是**頁面 JS 執行後**才生效，不是伺服器
最原始送出的 HTML 就有——如果 iOS 讀取圖示的時機比這更早，還是可能抓不到，
這是 Streamlit 平台本身的限制，目前沒有更進一步的解法。

### 4.4 Streamlit 的 onboarding email 提示會卡死非互動式啟動
第一次執行 `streamlit run` 沒加 `--server.headless true` 時，會卡在一個互動式的
「輸入 email（可留白）」提示等待輸入，非互動環境（例如批次檔啟動、CI）會整個掛住。
本機的 `啟動網頁介面.bat` 已經加上 `--server.headless true`，並額外用一個延遲的
`start http://localhost:8501` 來補回「自動開瀏覽器」的行為（headless 模式本身不會
自動開瀏覽器）。

---

## 5. 手機（iOS）UX 的坑

### 5.1 `data:` URI 不能拿去做「開新分頁導覽」
現代瀏覽器（Chrome、Safari 都一樣）為了防釣魚，會擋掉「導覽到 `data:` 開頭網址」
這個動作（不管是 `window.open()` 還是一般連結點擊）。原本想用 `st.link_button`
開新分頁顯示 PDF 的 `data:` URI，結果就是空白頁。

**正確做法**：改用 **Blob URL**（`URL.createObjectURL(blob)`，透過 JS 在瀏覽器端
動態把 base64 轉成檔案物件），這個機制不受上述限制，`window.open(blobUrl, '_blank')`
可以正常開新分頁。見 `app_streamlit.py` 裡的 `components.html` 區塊。

### 5.2 `<a download>` 在 iPhone Safari 上常常不會真的觸發下載
iOS Safari 對 `download` 屬性的支援不穩定，常常改成觸發系統層級的 Quick Look
全螢幕預覽，把目前頁面整個蓋掉；如果是從「加入主畫面」的捷徑開啟，關閉 Quick Look
後有時甚至無法回到原本頁面，只能重開 App。改用 Blob URL + `window.open()`
可以繞開這個問題（見上）。

### 5.3 Streamlit 按鈕點擊會讓整頁重新執行，結果沒存 session_state 就會消失
`st.download_button` 本身點擊也會觸發整頁重新執行（rerun）。如果查詢結果只存在
一般的區域變數裡（不是 `st.session_state`），下載當下這個結果就會在重新執行時
消失不見，畫面看起來像「整個 App 重置了」，容易誤以為要重新整理/重啟才能再查
下一檔。**已修正**：查詢結果存進 `st.session_state["report_result"]`，任何後續互動
（含下載按鈕本身）都不會讓它消失。

### 5.4 `components.html` 是獨立的 sandboxed iframe
`streamlit.components.v1.html()` 渲染的內容跑在一個獨立的 iframe 裡，`document`
指的是那個 iframe 自己的 document，不是外層主頁面。要碰外層頁面的 DOM（例如插入
`<link>` 到 `<head>`）理論上要用 `window.parent.document`，但這個做法在 Streamlit
Cloud 上是否會被額外安全性限制擋下還沒把握（見 4.3，最後是用 `st.markdown` 取代）。
如果只是要放一個會被使用者點擊、觸發 JS 邏輯的按鈕（例如 Web Share API），
`components.html` 本身沒問題，不需要跨到 `window.parent`。

---

## 6. 已知限制（目前沒有解法，非 bug）

- **上櫃股票沒有股價官方備援**：只驗證過 TWSE `STOCK_DAY` 這個上市股票的官方端點；
  TPEx（櫃買中心）新版網站找不到穩定可用的對應端點，上櫃股票股價目前只有 FinMind
  一層，沒有備援。
- **資產負債表/現金流量表/損益表明細沒有官方備援**：只有 FinMind 一層。
- **目標價/評等資料時有時無**：見 3.2 / 3.3，取決於當下鉅亨網有沒有相關新聞。
- **iOS「加入主畫面」自訂圖示不保證生效**：見 4.3，Streamlit Cloud 平台本身的限制。
- **基本面自檢表 / 本益比河流圖的公式都不是官方統一標準**：ROE/ROA 用近 8 季 TTM、
  現金轉換率＝營業現金流／稅後淨利、利息保障倍數＝(稅前淨利＋利息費用)／利息費用、
  本益比河流圖用 10/30/50/70/90 分位數——這些都是財務教學上常見但非唯一的定義，
  已在 PDF 報告內文與程式註解中揭露計算方式，不是隱藏假設。

---

## 7. 如果要繼續開發，建議先看這幾個檔案

- `report.py` — 所有資料怎麼串起來的，加新功能大概率要碰這裡
- `models.py` — 所有資料結構定義在這
- `providers/base.py` — `safe_provider` 裝飾器，新增 provider 一定要套用這個
- `pdf/builder.py` — PDF 每個區塊怎麼組出來的
