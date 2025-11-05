from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def parse_arguments() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="将单个 CSV 文件转换为 XLSX 文件。")
    parser.add_argument("input_csv", type=str, help="需要转换的 CSV 文件路径。")
    parser.add_argument(
        "output_xlsx",
        type=str,
        nargs="?",
        help="输出 XLSX 文件路径（默认为输入文件同名）。",
    )
    parser.add_argument(
        "--sheet-name",
        type=str,
        default="Sheet1",
        help="Excel 工作表名称，默认为 Sheet1。",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        default="utf-8-sig",
        help="读取 CSV 时使用的编码，默认为 utf-8-sig。",
    )
    return parser.parse_args()


def _ensure_output_path(input_csv: Path, output_hint: str | None) -> Path:
    """Resolve the output path, forcing the .xlsx suffix."""
    if output_hint:
        output_path = Path(output_hint)
    else:
        output_path = input_csv.with_suffix(".xlsx")

    if output_path.suffix.lower() != ".xlsx":
        output_path = output_path.with_suffix(".xlsx")

    return output_path


def convert_csv_to_xlsx(
    input_csv: Path, output_xlsx: Path, *, sheet_name: str, encoding: str
) -> None:
    """
    Convert a CSV file into an Excel workbook.

    Args:
        input_csv: Source CSV file path.
        output_xlsx: Destination XLSX file path.
        sheet_name: Excel sheet name to use.
        encoding: Encoding used to read the CSV.
    """
    if not input_csv.exists():
        raise FileNotFoundError(f"未找到输入文件: {input_csv}")

    if input_csv.suffix.lower() != ".csv":
        raise ValueError("只支持以 .csv 结尾的输入文件。")

    output_xlsx.parent.mkdir(parents=True, exist_ok=True)
    dataframe = pd.read_csv(input_csv, encoding=encoding)
    dataframe.to_excel(output_xlsx, sheet_name=sheet_name, index=False, engine="openpyxl")


def main() -> None:
    """CLI entry point."""
    args = parse_arguments()
    input_csv = Path(args.input_csv).expanduser().resolve()
    output_xlsx = _ensure_output_path(input_csv, args.output_xlsx)

    try:
        convert_csv_to_xlsx(
            input_csv,
            output_xlsx,
            sheet_name=args.sheet_name,
            encoding=args.encoding,
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"❌ {exc}")
        raise SystemExit(1) from exc

    print(f"✅ 已生成 Excel 文件: {output_xlsx}")


if __name__ == "__main__":
    main()
