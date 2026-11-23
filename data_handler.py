from datetime import date
from pathlib import Path

import os
import pandas as pd



DEFAULT_DATA_DIR = Path(__file__).resolve().parents[0] / "data"
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_PRICE_FILE = DEFAULT_DATA_DIR / "prices.csv"
DEFAULT_INDEX_FILE = DEFAULT_DATA_DIR / "indexes.csv"
DEFAULT_TRADE_DATES_FILE = DEFAULT_DATA_DIR / "trade_dates.csv"

def _tushare_client():
    import tushare as ts

    return ts.pro_api(os.environ["TUSHARE_TOKEN"])


class DataHandler:
    def __init__(self, symbol_list, start_date, end_date):
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.end_date = end_date

        self.data = self.read_data_from_csv()
        self.trade_dates = self.read_trade_dates_from_csv()

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

    def read_data_from_csv(self):

        prices = pd.read_csv(DEFAULT_PRICE_FILE, dtype={"ts_code": str, "trade_date": str})

        period_prices = prices.loc[
            prices["trade_date"].between(self.start_date, self.end_date)
        ]

        data = {
            symbol: rows for symbol, rows in period_prices.groupby("ts_code", sort=False)
        }
        return data

    def read_trade_dates_from_csv(self) -> list[str]:
        trade_dates = pd.read_csv(DEFAULT_TRADE_DATES_FILE,dtype=str)["trade_date"]
        selected = trade_dates[trade_dates.between(self.start_date, self.end_date)]
        return sorted(selected.tolist())

    def get_value(self, symbol: str, datetime: str | int | date, value_type: str):

        trade_date = datetime.strftime("%Y%m%d") if isinstance(datetime, date) else str(datetime)
        prices = self.data[symbol]
        values = prices.loc[prices["trade_date"] == trade_date, value_type]
        return values.item()

    def get_valuation_close(self, symbol: str, datetime: str | int | date):

        trade_date = datetime.strftime("%Y%m%d") if isinstance(datetime, date) else str(datetime)
        prices = self.data[symbol]
        dates = prices["trade_date"]
        pre_prices = prices.loc[
            (dates <= trade_date)
            & dates.isin(self.trade_dates)
            & prices['close'].notna()
            ]
        if pre_prices.empty:
            raise ValueError(f"{symbol} 在 {trade_date} 及之前没有可用的收盘价")

        latest_date = pre_prices["trade_date"].max()
        return pre_prices.loc[pre_prices["trade_date"] == latest_date, 'close'].item()

if __name__ == "__main__":

    symbol_list = ['000001.SZ', '000011.SZ','000025.SZ','600519.SH']
    index_list = ['000001.SH', '399300.SZ', '000852.SH', '000688.SH']
    start_date = '20240101'
    end_date = '20261001'
    DataHandler.save_data_to_csv(symbol_list,start_date,end_date)
    DataHandler.save_indexes_to_csv(index_list,start_date,end_date)
    DataHandler.save_trade_dates_to_csv(start_date,end_date)


