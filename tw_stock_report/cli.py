"""命令列介面：py -m tw_stock_report.cli --stock 2330"""
from __future__ import annotations

import argparse
import sys

from .identity import IdentityNotFound
from .report import generate_report


def main() -> int:
    parser = argparse.ArgumentParser(description="台股投資分析 PDF 報告產生器")
    parser.add_argument("--stock", required=True, help="股票代號或名稱，例如 2330 或 台積電")
    args = parser.parse_args()

    try:
        result = generate_report(args.stock)
    except IdentityNotFound as exc:
        print(f"錯誤：{exc}", file=sys.stderr)
        return 1

    print(f"報告已產出：{result.pdf_path}")
    print("各模組資料來源狀態：")
    for status in result.data.source_statuses:
        mark = "OK" if status.ok else "!!"
        line = f"  [{mark}] {status.module}：{status.source_used}"
        if status.message:
            line += f"（{status.message}）"
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
