from bisect import bisect_left
from datetime import date, timedelta

import pandas as pd

from datahandler.abstract_data_handler import DEFAULT_TRADE_DATES_FILE


def read_mo_expiry_dates() -> dict[str, str]:
    """返回合约系列对应的到期日，例如 {"MO2303": "20230317"}。"""
    calendar = pd.read_csv(DEFAULT_TRADE_DATES_FILE, dtype={"trade_date": str})
    days = sorted(set(calendar["trade_date"]))
    expiry_dates = {}

    for month in sorted({day[:6] for day in days}):
        # 每月 15 日至 21 日之间的星期五，就是第三个星期五。
        day15 = date(int(month[:4]), int(month[4:]), 15)
        third_friday = day15 + timedelta(days=(4 - day15.weekday()) % 7)

        # 找到当天或其后的第一个交易日。
        index = bisect_left(days, third_friday.strftime("%Y%m%d"))
        if index < len(days):
            series = "MO" + month[2:]  # "202303" -> "MO2303"
            expiry_dates[series] = days[index]

    return expiry_dates