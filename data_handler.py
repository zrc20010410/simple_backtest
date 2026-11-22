from datetime import date
from pathlib import Path

import tushare as ts
import pandas as pd

ts.set_token('bb1f02d94529abe3a08fc3de093633253e2b904f82b5406fb796633c')
pro = ts.pro_api()

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[0] / "data"


class DataHandler:
    def __init__(self, symbol_list, start_date, end_date,refresh_data: bool = False):
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.end_date = end_date

        self.data_dir = DEFAULT_DATA_DIR
        self.data_dir.mkdir(parents=True, exist_ok=True)
        path = self.data_dir / f"price_{start_date}_{end_date}.csv"

        if refresh_data:
            self.save_data_to_csv(path, self.symbol_list, self.start_date, self.end_date)
        self.data = self.read_data_from_csv(path)

    @staticmethod
    def save_data_to_csv(path, symbol_list, start_date, end_date):

        frames = []
        for symbol in symbol_list:
            data = (pro.daily(ts_code=symbol, start_date=start_date, end_date=end_date)
                    .sort_values("trade_date", ascending=True, ignore_index=True))
            if not data.empty:
                frames.append(data)

        df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

        df.to_csv(path, index=False)
        return df

    @staticmethod
    def read_data_from_csv(path):

        prices = pd.read_csv(path, dtype={"ts_code": str, "trade_date": str})

        data = {
            symbol: rows for symbol, rows in prices.groupby("ts_code", sort=False)
        }
        return data

    def get_value(self, symbol: str, datetime: str | int | date, value_type: str):
        """按股票代码和交易日（YYYYMMDD 或日期对象）读取一个行情字段。"""
        trade_date = datetime.strftime("%Y%m%d") if isinstance(datetime, date) else str(datetime)
        prices = self.data[symbol]
        values = prices.loc[prices["trade_date"] == trade_date, value_type]
        return values.item()


if __name__ == "__main__":

    symbol_list = ['000001.SZ', '000011.SZ','000025.SZ','600519.SH']
    start_date = '20260101'
    end_date = '20260401'
    data_handler = DataHandler(symbol_list,start_date,end_date)


