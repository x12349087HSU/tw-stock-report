# 台股投資分析 PDF 報告產生器

輸入台股代號或名稱，自動彙整公開資料（股價、營收、EPS、新聞、產業趨勢、公開可得評等/目標價），
產出一份中文 PDF 投資分析報告。

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

```powershell
.venv\Scripts\python -m streamlit run tw_stock_report/app_streamlit.py
```

在瀏覽器輸入股票代號或名稱，點擊按鈕即可產生並下載 PDF。

## 資料來源

- 股價 / 月營收 / EPS：[FinMind](https://finmind.github.io/) 公開 API（免登入），失敗時改用證交所
  OpenAPI / 公開資訊觀測站（MOPS）官方來源。
- 新聞：MoneyDJ、鉅亨網、經濟日報（UDN money）等公開新聞頁面，多來源、多關鍵字、三層 fallback。
- 目標價與評等：非官方 API，改為從公開新聞標題/摘要中以關鍵字與規則式解析整理，僅供參考。

## 重要聲明

所有投資相關內容僅供參考，不構成任何投資建議，使用者應自行評估風險。
本工具僅整理公開可得資訊，不繞過任何網站的登入、付費牆或 robots.txt 限制。
