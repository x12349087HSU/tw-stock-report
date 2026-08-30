# 台股投資分析 PDF 報告產生器

輸入台股代號或名稱，自動彙整公開資料（股價、營收、EPS、財報、新聞、產業趨勢、
公開可得評等/目標價），產出一份中文 PDF 投資分析報告。支援命令列與網頁介面
（本機或 Streamlit Community Cloud 雲端部署，含手機瀏覽器）兩種用法。

開發過程中的關鍵決策、踩過的坑、已知限制，請見 [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md)。

## 安裝

```powershell
py -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

## 使用方式

### 命令列 (CLI)

```powershell
.venv\Scripts\python -m tw_stock_report.cli --stock 2330
.venv\Scripts\python -m tw_stock_report.cli --stock 台積電
```

產出的 PDF 會存在 `reports/` 目錄下，並在終端機印出各資料模組的成功/降級狀態。

### 網頁介面 (Streamlit)

**本機執行**：

```powershell
.venv\Scripts\python -m streamlit run tw_stock_report/app_streamlit.py
```

Windows 也可以直接雙擊專案根目錄的 `啟動網頁介面.bat`（或桌面上對應的捷徑），
會自動啟動服務並開啟瀏覽器，不用手動打指令。

**雲端部署**：本專案已設計為可直接部署到 [Streamlit Community Cloud](https://share.streamlit.io)
（免費），部署後手機/電腦在任何有網路的地方都能使用，不需要本機電腦開機。部署步驟：

1. 到 share.streamlit.io 用 GitHub 帳號登入並授權
2. 選擇這個 repo，Main file path 填 `tw_stock_report/app_streamlit.py`
3.（選用）要開啟密碼保護，在 Advanced settings 的 Secrets 填入：
   ```toml
   APP_PASSWORD = "你的密碼"
   ```
   本機執行時若未設定 `APP_PASSWORD`（環境變數或 `.streamlit/secrets.toml`），
   則不會要求輸入密碼。

在瀏覽器（含手機）輸入股票代號或名稱、按「產生報告」，可重複查詢不需要重新整理頁面；
產生後可選擇「用瀏覽器開啟 PDF」（新分頁預覽）、「選擇開啟方式」（叫出系統分享選單）
或「下載 PDF 到裝置」。

## 報告內容

一、個股基本資訊　二、股價走勢分析（3/6/12 個月線圖，近一年圖疊加 5/10/20/60 日均線，
含本益比河流圖）　三、近兩年營收分析　四、EPS 分析　五、新聞與研究摘要　六、目標價與
投資評等　七、核心成長動能基本面自檢表（營收/EPS 成長、ROE/ROA、財務體質、獲利能力
趨勢四層指標）　最後固定附上投資免責聲明。

## 資料來源

- **股價 / 月營收 / EPS / 財報明細**：[FinMind](https://finmind.github.io/) 公開 API（免登入）
  為主；股價、月營收、EPS 失敗時改用證交所 OpenAPI / 公開資訊觀測站（MOPS）官方來源備援，
  資產負債表與現金流量表目前僅有 FinMind 一層。
- **新聞**：FinMind 個股新聞聚合資料集 + 鉅亨網（news.cnyes.com）關鍵字搜尋，多關鍵字、
  三層 fallback。*未使用 MoneyDJ / 經濟日報等站台*——這幾個站台的 robots.txt 明確
  disallow AI 爬蟲，詳見 DEVELOPMENT_LOG.md。
- **目標價與評等**：非官方 API，從鉅亨網新聞標題/摘要中以關鍵字與規則式解析整理，
  查無資料是正常情況，不代表程式錯誤。

## 已知限制

上櫃股票股價、資產負債表、現金流量表目前沒有官方備援；iOS「加入主畫面」的自訂圖示
在 Streamlit Cloud 上不保證每次都生效；基本面自檢表與本益比河流圖的公式為財務教學上
常見但非官方統一標準。完整說明見 [DEVELOPMENT_LOG.md](DEVELOPMENT_LOG.md) 第 6 節。

## 重要聲明

所有投資相關內容僅供參考，不構成任何投資建議，使用者應自行評估風險。
本工具僅整理公開可得資訊，不繞過任何網站的登入、付費牆或 robots.txt 限制。
