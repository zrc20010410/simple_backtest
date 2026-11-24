"""将 data/opt_eod/tik/YYYYMMDD 里的 MO 合约行情按日合并。"""

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


if __name__ == "__main__":
    days, files, rows = organize_data()
    print(f"已合并 {files:,} 个 MO 合约文件，生成 {days:,} 个日文件，共 {rows:,} 条行情。")
