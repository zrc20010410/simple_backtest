"""整理 MO 期权日行情和中证 1000 指数日线。"""

import csv
import re
from concurrent.futures import ThreadPoolExecutor
from itertools import repeat
from pathlib import Path
from tempfile import NamedTemporaryFile

DATA_DIR = Path(r"D:\code")
MO_FILE = re.compile(r"MO[0-9]{4}-[CP]-[0-9]+(?:\.[0-9]+)?\.csv", re.IGNORECASE)


def _merge_day(day_dir: Path, output_dir: Path) -> tuple[int, int]:
    contracts = sorted(p for p in day_dir.iterdir() if MO_FILE.fullmatch(p.name) and p.is_file())
    if not contracts:
        return 0, 0

    columns = {}
    rows = []
    for contract in contracts:
        with contract.open(encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if not reader.fieldnames or not {"time", "product_id", "instrument_id"} <= set(reader.fieldnames):
                raise ValueError(f"{contract} 缺少行情表头")
            columns.update(dict.fromkeys(reader.fieldnames))
            for row in reader:
                if row["product_id"] != "MO" or row["instrument_id"] != contract.stem:
                    raise ValueError(f"{contract} 第 {reader.line_num} 行的品种或合约代码与文件名不符")
                rows.append(row)

    target = output_dir / f"{day_dir.name}.csv"
    temp = NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=output_dir,
                              prefix=f".{day_dir.name}-", suffix=".tmp", delete=False)
    temp_path = Path(temp.name)
    try:
        with temp:
            writer = csv.DictWriter(temp, fieldnames=list(columns))
            writer.writeheader()
            writer.writerows(rows)
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)
    return len(contracts), len(rows)


def organize_data(source_dir: Path = DATA_DIR / "opt_eod" / "tik",
                  output_dir: Path = Path(__file__).resolve().parent / "data" / "options") -> tuple[int, int, int]:
    """返回有 MO 数据的日期数、合约文件数和写出的行情记录数。"""
    source_dir, output_dir = Path(source_dir), Path(output_dir)
    days = sorted(p for p in source_dir.iterdir() if re.fullmatch(r"[0-9]{8}", p.name) and p.is_dir())
    output_dir.mkdir(parents=True, exist_ok=True)
    day_count = file_count = row_count = 0
    with ThreadPoolExecutor(max_workers=4) as pool:
        for files, rows in pool.map(_merge_day, days, repeat(output_dir)):
            if files:
                day_count += 1
                file_count += files
                row_count += rows
    return day_count, file_count, row_count


def organize_index_data(source_file: Path = DATA_DIR / "opt_eod" / "000852_日线数据.xlsx",
                        output_dir: Path = Path(__file__).resolve().parent / "data" / "indexes") -> Path:
    """将中证 1000 日线转为 000852.csv，保留原表的数值和涨跌幅单位（%）。"""
    import pandas as pd

    columns = {
        "证券代码": "index_code", "证券名称": "index_name", "交易时间": "trade_date",
        "开盘价": "open", "最高价": "high", "最低价": "low", "收盘价": "close",
        "涨跌": "change", "涨跌幅%": "pct_chg", "成交量": "volume", "成交额": "amount",
    }
    daily = pd.read_excel(source_file, usecols=list(columns), dtype={"证券代码": str},
                          keep_default_na=False, engine="openpyxl")
    daily = daily.rename(columns=columns)
    daily["trade_date"] = pd.to_datetime(daily["trade_date"]).dt.strftime("%Y%m%d")

    target = Path(output_dir) / "000852.csv"
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", dir=target.parent,
                              prefix=f".{target.name}-", suffix=".tmp", delete=False)
    temp_path = Path(temp.name)
    try:
        with temp:
            daily.to_csv(temp, columns=list(columns.values()), index=False)
        temp_path.replace(target)
    finally:
        temp_path.unlink(missing_ok=True)
    return target


if __name__ == "__main__":
    days, files, rows = organize_data()
    target = organize_index_data()
    print(f"已合并 {files:,} 个 MO 合约文件，生成 {days:,} 个日文件，共 {rows:,} 条行情。")
    print(f"指数日线已保存到 {target}")
