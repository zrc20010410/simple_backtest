import os
import pandas as pd
from abc import ABC, abstractmethod
from datetime import date
from config import DEFAULT_TRADE_DATES_FILE, DEFAULT_INDEX_DIR

def _tushare_client():
    import tushare as ts
    return ts.pro_api(os.environ["TUSHARE_TOKEN"])

class AbstractDataHandler(ABC):
    def __init__(self, symbol_list: list[str], start_date: str, end_date: str):
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.end_date = end_date
        self.trade_dates = self.read_trade_dates_from_csv()

    def read_trade_dates_from_csv(self) -> list[str]:
        trade_dates = pd.read_csv(DEFAULT_TRADE_DATES_FILE,usecols=["trade_date"],dtype=str)["trade_date"]
        selected = trade_dates[trade_dates.between(self.start_date, self.end_date)]
        if selected.empty:
            raise ValueError(f'{self.start_date} 至 {self.end_date} 没有交易日')
        return sorted(selected.tolist())

    def _read_index_data_from_csv(self) -> pd.DataFrame:
        """读取回测起止日期内的指数日线"""
        index_data = pd.read_csv(
            DEFAULT_INDEX_DIR / "000852.csv",
            dtype={"index_code": str, "trade_date": str},
            na_values=["--"],
        ).sort_values("trade_date")
        index_data["pre_close"] = index_data["close"].shift(1)
        in_period = index_data["trade_date"].between(self.start_date, self.end_date)
        return index_data.loc[in_period].reset_index(drop=True)

    @staticmethod
    def save_trade_dates_to_csv(start_date, end_date):
        pro = _tushare_client()
        # 保存交易日列表
        calendar = pro.trade_cal(exchange="SSE", start_date=start_date, end_date=end_date)
        trade_dates = sorted(
            calendar.loc[calendar["is_open"].astype(str) == "1", "cal_date"].astype(str)
        )
        pd.DataFrame({"trade_date": trade_dates}).to_csv(DEFAULT_TRADE_DATES_FILE, index=False)

    @abstractmethod
    def get_value(self, symbol: str, datetime: str | int | date, value_type: str):
        """读取指定标的、指定交易日的行情字段。"""
        ...