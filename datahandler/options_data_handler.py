import re
import pandas as pd
from datetime import date
from math import isfinite
from datahandler.abstract_data_handler import AbstractDataHandler
from config import DEFAULT_OPTION_DAILY_DIR
from utils.mo_expiry import read_mo_expiry_dates

_PRICE_FIELDS = {
    "open": "open_price",
    "close": "close_price",
    "settle": "settle_price",
    "pre_settle": "pre_settle_price",
}

def _date_to_str(value: str | int | date) -> str:
    return value.strftime("%Y%m%d") if isinstance(value, date) else str(value)

class OptionsDataHandler(AbstractDataHandler):

    contract_multiplier = 100
    margin_adjustment = 0.12
    minimum_protection = 0.5

    def __init__(self, symbol_list, start_date, end_date):
        super().__init__(symbol_list, _date_to_str(start_date), _date_to_str(end_date))
        self.option_data = self._read_data_from_csv()
        self.index_data = self._read_index_data_from_csv()
        self.expiry_dates = read_mo_expiry_dates()

    def _read_data_from_csv(self) -> dict[str, pd.DataFrame]:
        """读取回测起止日期内标的数据"""
        quote_columns = ['instrument_id', 'open_price', 'close_price', 'settle_price', 'pre_settle_price']
        frames = []
        for trade_date in self.trade_dates:
            path = DEFAULT_OPTION_DAILY_DIR / f"{trade_date}.csv"
            if not path.is_file():
                break
            daily = pd.read_csv(path, usecols=quote_columns, dtype={"instrument_id": str})
            daily["trade_date"] = trade_date
            frames.append(daily)
        if not frames:
            return {}

        prices = pd.concat(frames, ignore_index=True)[[*quote_columns, "trade_date"]]
        return {symbol: rows for symbol, rows in prices.groupby("instrument_id", sort=False)}

    def get_value(self, symbol: str, datetime: str | int | date, value_type: str):
        trade_date = _date_to_str(datetime)
        if symbol not in self.option_data:
            raise KeyError(f"没有期权合约 {symbol} 的行情")
        prices = self.option_data[symbol]
        field = _PRICE_FIELDS.get(value_type, value_type)
        if field not in prices.columns:
            raise KeyError(f"{symbol} 的期权行情没有字段 {value_type}")
        values = prices.loc[prices["trade_date"] == trade_date, field]
        if values.empty:
            raise KeyError(f"{symbol} 在 {trade_date} 没有行情记录")
        value = values.item()
        if pd.isna(value):
            raise ValueError(f"{symbol} 在 {trade_date} 的 {field} 缺失")
        if field in _PRICE_FIELDS.values():
            price = float(value)
            if not isfinite(price) or price < 0:
                raise ValueError(f"{symbol} 在 {trade_date} 的 {field} 无效：{value!r}")
            return price
        return value

    def _get_index_price(self, trade_date: str | int | date, field: str) -> float:
        day = _date_to_str(trade_date)
        values = self.index_data.loc[self.index_data["trade_date"] == day, field]
        if len(values) != 1:
            raise ValueError(f"中证1000在 {day} 应有一条指数行情，实际有 {len(values)} 条")
        value = values.item()
        if pd.isna(value):
            raise ValueError(f"中证1000在 {day} 的 {field} 缺失")
        price = float(value)
        if not isfinite(price) or price <= 0:
            raise ValueError(f"中证1000在 {day} 的 {field} 须为有限正数，实际为 {price}")
        return price

    def get_margin_inputs(
        self, symbol: str, datetime: str | int | date, *, at_open: bool = False,
    ):
        """返回每手 MO 卖方保证金的公式参数。开仓取当日记录的前值，日终取当日值。"""
        contract = re.fullmatch(r"MO\d{2}(?:0[1-9]|1[0-2])-([CP])-(\d+(?:\.\d+)?)", symbol)
        if contract is None:
            raise ValueError(f"无法解析 MO 合约代码 {symbol!r}")

        settle_field, index_field = ("pre_settle", "pre_close") if at_open else ("settle", "close")
        return {
            "option_type": contract.group(1),
            "strike": float(contract.group(2)),
            "settle": self.get_value(symbol, datetime, settle_field),
            "index_close": self._get_index_price(datetime, index_field),
            "multiplier": self.contract_multiplier,
            "a": self.margin_adjustment,
            "b": self.minimum_protection,
        }
