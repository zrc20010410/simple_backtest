from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path

import pandas as pd

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_DATA_DIR.mkdir(parents=True, exist_ok=True)
DEFAULT_TRADE_DATES_FILE = DEFAULT_DATA_DIR / "trade_dates.csv"

class ABSDataHandler(ABC):
    def __init__(self, symbol_list: list[str], start_date: str, end_date: str):
        self.symbol_list = symbol_list
        self.start_date = start_date
        self.end_date = end_date
        self.trade_dates = self.read_trade_dates_from_csv()

    def read_trade_dates_from_csv(self) -> list[str]:
        trade_dates = pd.read_csv(DEFAULT_TRADE_DATES_FILE,usecols=["trade_date"],dtype=str)["trade_date"]
        selected = trade_dates[trade_dates.between(self.start_date, self.end_date)]
        return sorted(selected.tolist())

    @abstractmethod
    def get_value(self, symbol: str, datetime: str | int | date, value_type: str):
        """读取指定标的、指定交易日的行情字段。"""
        ...