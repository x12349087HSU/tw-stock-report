@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 台股投資分析 PDF 報告產生器
echo 正在啟動「台股投資分析 PDF 報告產生器」網頁介面...
echo 瀏覽器將在幾秒後自動開啟，若沒有請手動開啟 http://localhost:8501
echo 要關閉服務，請直接關閉這個視窗（或按 Ctrl+C）。
echo.

start "" cmd /c "timeout /t 4 /nobreak >nul && start http://localhost:8501"

".venv\Scripts\python.exe" -m streamlit run tw_stock_report/app_streamlit.py --server.port 8501 --server.headless true

pause
