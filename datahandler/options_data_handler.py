import pandas as pd
from datetime import date
from math import isfinite
from datahandler.abs_data_handler import ABSDataHandler, DEFAULT_DATA_DIR

DEFAULT_OPTIONS_DIR = DEFAULT_DATA_DIR / "options"

_PRICE_FIELDS = {
    "open": "open_price",
    "close": "close_price",
    "settle": "settle_price",
}

def _date_to_str(value: str | int | date) -> str:
    return value.strftime("%Y%m%d") if isinstance(value, date) else str(value)


class OptionsDataHandler(ABSDataHandler):
    def __init__(self, symbol_list, start_date, end_date):
        super().__init__(symbol_list, _date_to_str(start_date), _date_to_str(end_date))
        self.option_data = self._read_data_from_csv()

    @property
    def options_data(self) -> dict[str, pd.DataFrame]:
        """兼容原来的属性名，共用同一份行情。"""
        return self.option_data

    def read_trade_dates_from_csv(self) -> list[str]:
        """每日行情文件名即交易日期，只读取起止日期之间的文件。"""
        return sorted(
            path.stem for path in DEFAULT_OPTIONS_DIR.iterdir()
            if path.suffix == ".csv" and len(path.stem) == 8 and path.stem.isdigit()
            and self.start_date <= path.stem <= self.end_date and path.is_file()
        )

    def _read_data_from_csv(self) -> dict[str, pd.DataFrame]:
        quote_columns = ['instrument_id', 'open_price', 'close_price', 'settle_price']
        frames = []
        for trade_date in self.trade_dates:
            path = DEFAULT_OPTIONS_DIR / f"{trade_date}.csv"
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



