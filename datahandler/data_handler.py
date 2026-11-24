import os
import pandas as pd
from datetime import date
from math import isfinite
from datahandler.abs_data_handler import ABSDataHandler,DEFAULT_DATA_DIR,DEFAULT_TRADE_DATES_FILE

DEFAULT_STOCKS_DIR = DEFAULT_DATA_DIR / "stocks"
DEFAULT_PRICE_FILE = DEFAULT_STOCKS_DIR / "prices.csv"
DEFAULT_INDEX_FILE = DEFAULT_STOCKS_DIR / "indexes.csv"

def _tushare_client():
    import tushare as ts
    return ts.pro_api(os.environ["TUSHARE_TOKEN"])

class DataHandler(ABSDataHandler):
    def __init__(self, symbol_list, start_date, end_date):
        super().__init__(symbol_list, start_date, end_date)
        # self.data = self._read_data_from_csv()

    @staticmethod
    def save_data_to_csv(symbol_list, start_date, end_date):
        pro = _tushare_client()
        # 保存股票行情信息
        frames = []
        for symbol in symbol_list:
            data = (pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
                    .sort_values("trade_date", ascending=True, ignore_index=True))
            if not data.empty:
                frames.append(data)

        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        df.to_csv(DEFAULT_PRICE_FILE, index=False)

    @staticmethod
    def save_indexes_to_csv(index_list, start_date, end_date):
        pro = _tushare_client()
        # 保存指数行情信息
        frames = []
        for index in index_list:
            data = (pro.index_daily(ts_code=index, start_date=start_date, end_date=end_date)
                    .sort_values("trade_date", ascending=True, ignore_index=True))
            if not data.empty:
                frames.append(data)

        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        df.to_csv(DEFAULT_INDEX_FILE, index=False)

    @staticmethod
    def save_trade_dates_to_csv(start_date, end_date):
        pro = _tushare_client()
        # 保存交易日列表
        calendar = pro.trade_cal(exchange="SSE", start_date=start_date, end_date=end_date)
        trade_dates = sorted(
            calendar.loc[calendar["is_open"].astype(str) == "1", "cal_date"].astype(str)
        )
        pd.DataFrame({"trade_date": trade_dates}).to_csv(DEFAULT_TRADE_DATES_FILE, index=False)

    def _read_data_from_csv(self):

        prices = pd.read_csv(DEFAULT_PRICE_FILE, dtype={"ts_code": str, "trade_date": str})

        period_prices = prices.loc[
            prices["trade_date"].between(self.start_date, self.end_date)
        ]

        data = {
            symbol: rows for symbol, rows in period_prices.groupby("ts_code", sort=False)
        }
        return data

    def get_value(self, symbol: str, datetime: str | int | date, value_type: str):
        trade_date = datetime.strftime("%Y%m%d") if isinstance(datetime, date) else str(datetime)

        if symbol not in self.data:
            raise KeyError(f"没有股票 {symbol} 的行情数据")

        prices = self.data[symbol]
        if value_type not in prices.columns:
            raise KeyError(f"{symbol} 的行情中没有字段 {value_type}")

        values = prices.loc[prices["trade_date"] == trade_date, value_type]
        if values.empty:
            raise KeyError(f"{symbol} 在 {trade_date} 没有行情记录")

        value = values.item()
        if pd.isna(value):
            raise ValueError(f"{symbol} 在 {trade_date} 的 {value_type} 缺失")

        if value_type in {"open", "high", "low", "close", "pre_close"}:
            price = pd.to_numeric(str(value), errors="coerce")
            if not isfinite(price) or price <= 0:
                raise ValueError(f"{symbol} 在 {trade_date} 的 {value_type} 无效：{value!r}")
            return float(price)

        return value

    def get_valuation_close(self, symbol: str, datetime: str | int | date):
        trade_date = datetime.strftime("%Y%m%d") if isinstance(datetime, date) else str(datetime)
        prices = self.data[symbol]
        dates = prices["trade_date"]

        close = pd.to_numeric(prices["close"].astype("string"), errors="coerce")
        valid = (
                dates.le(trade_date)
                & dates.isin(self.trade_dates)
                & close.gt(0)
                & close.lt(float("inf"))
        )
        if not valid.any():
            raise ValueError(f"{symbol} 在 {trade_date} 及之前没有可用的收盘价")

        latest_date = dates.loc[valid].max()
        return float(close.loc[valid & dates.eq(latest_date)].item())

if __name__ == "__main__":

    symbol_list = ['000001.SZ', '000011.SZ','000025.SZ','600519.SH']
    # index_list = ['000001.SH', '399300.SZ', '000852.SH', '000688.SH']
    index_list = ['399300.SZ']
    start_date = '20230101'
    end_date = '20261008'
    # DataHandler.save_data_to_csv(symbol_list,start_date,end_date)
    # DataHandler.save_indexes_to_csv(index_list,start_date,end_date)
    DataHandler.save_trade_dates_to_csv(start_date,end_date)


