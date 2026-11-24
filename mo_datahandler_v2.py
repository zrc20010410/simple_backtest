"""本地中证 1000 股指期权日终行情，读取指定日期与合约的归档文件。"""

import csv
import re
from datetime import date
from functools import lru_cache
from math import isfinite
from pathlib import Path

from datahandler.abs_data_handler import ABSDataHandler
from mo_margin_v2 import MO_MULTIPLIER, mo_margin_for_day, mo_margin_rates


DEFAULT_MO_DATA_DIR = Path(__file__).resolve().parent / "data" / "opt_eod"
_MO_SYMBOL = re.compile(r"(MO[0-9]{2}(?:0[1-9]|1[0-2])-[CP]-[0-9]+(?:\.[0-9]+)?)(?:\.(?:CFX|CFE|CFFEX))?")


def _day(value):
    if not isinstance(value, date):
        value = date.fromisoformat(str(value))
    return value.strftime("%Y%m%d")


def _number(row, field, path):
    try:
        number = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"{path} 的 {field} 缺失或无效") from exc
    if not isfinite(number) or number < 0:
        raise ValueError(f"{path} 的 {field} 无效：{number}")
    return number


@lru_cache(maxsize=32)
def _index_close(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = [r for r in csv.DictReader(source) if r["代码"].lower() == "sh000852"]
    if len(rows) != 1:
        raise ValueError(f"{path} 应当包含一条 sh000852 日终记录")
    close = _number(rows[0], "最新价", path)
    if close == 0:
        raise ValueError(f"{path} 的中证1000指数收盘价为零")
    return close


@lru_cache(maxsize=32)
def _multipliers(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        return {r["InstrumentID"]: _number(r, "VolumeMultiple", path)
                for r in csv.DictReader(source) if r["ProductID"] == "MO"}


@lru_cache(maxsize=256)
def _quote(path, symbol, day):
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = [r for r in csv.DictReader(source)
                if r["instrument_id"] == symbol and r["time"].startswith(day)]
    if not rows:
        raise ValueError(f"{path} 中缺少 {day} 的 {symbol} 日终行情")
    return max(rows, key=lambda r: r["time"])


class MODataHandler(ABSDataHandler):
    """std/<日期> 为日终静态与指数数据，tik/<日期> 为对应合约行情。

    margin_rates 按生效日配置 (调整系数, 最低保障系数)，系数使用小数。
    开仓取上一归档交易日的日终标准；首次挂牌等缺少前结算标准的情形需另给数据。
    """

    def __init__(self, symbol_list, start_date, end_date, *, data_dir=DEFAULT_MO_DATA_DIR,
                 margin_rates=None):
        self.data_dir = Path(data_dir)
        self.margin_rates = margin_rates
        days = sorted(p.name for p in (self.data_dir / "std").iterdir()
                      if p.name.isdigit() and len(p.name) == 8 and p.is_dir() and any(p.iterdir()))
        self._previous = dict(zip(days[1:], days))
        self._days = days
        super().__init__(symbol_list, _day(start_date), _day(end_date))

    def read_trade_dates_from_csv(self):
        return [day for day in self._days if self.start_date <= day <= self.end_date]

    def get_value(self, symbol, datetime, value_type):
        match = _MO_SYMBOL.fullmatch(symbol.upper())
        if match is None:
            raise ValueError(f"无效 MO 合约代码：{symbol}")
        contract = match.group(1)
        day = _day(datetime)
        std = self.data_dir / "std" / day

        if value_type == "underlying_close":
            return _index_close(std / "idx.csv")
        if value_type == "multiplier":
            path = std / "static.csv"
            if path.is_file():
                multiplier = _multipliers(path).get(contract)
                if multiplier != MO_MULTIPLIER:
                    raise ValueError(f"{contract} 在 {day} 的合约乘数应为 {MO_MULTIPLIER}，归档值为 {multiplier}")
            return MO_MULTIPLIER
        if value_type in ("margin_adjustment", "minimum_protection"):
            adjustment, floor = mo_margin_rates(day, self.margin_rates)
            return adjustment if value_type == "margin_adjustment" else floor
        if value_type == "margin_per_contract":
            return mo_margin_for_day(self, contract, day)
        if value_type == "open_margin_per_contract":
            previous = self._previous.get(day)
            if previous is None:
                raise ValueError(f"{contract} 在 {day} 缺少上一交易日的保证金标准")
            try:
                return mo_margin_for_day(self, contract, previous)
            except FileNotFoundError as exc:
                raise ValueError(f"{contract} 在 {day} 开仓需要 {previous} 的结算数据") from exc

        fields = {"settle": "settle_price", "open": "open_price", "close": "close_price"}
        if value_type not in fields:
            raise KeyError(f"MO 行情不支持字段 {value_type}")
        path = self.data_dir / "tik" / day / f"{contract}.csv"
        return _number(_quote(path, contract, day), fields[value_type], path)

    def get_valuation_close(self, symbol, datetime):
        return self.get_value(symbol, datetime, "settle")
