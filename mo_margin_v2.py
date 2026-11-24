"""中金所《股指期权合约交易细则》第 23 条：MO 单腿义务仓日终保证金。"""

from collections.abc import Mapping
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from math import isfinite
import re


MO_MULTIPLIER = 100  # 元/指数点
_MO_CONTRACT = re.compile(r"MO\d{2}(?:0[1-9]|1[0-2])-([CP])-(\d+(?:\.\d+)?)(?:\.(?:CFX|CFE|CFFEX))?")


def mo_margin_rates(
    trade_date: str | date, schedule: Mapping[str, tuple[float, float]] | None
) -> tuple[float, float]:
    """选择截至该日已生效的（保证金调整系数，最低保障系数），日期键为 YYYYMMDD。"""
    day = trade_date.strftime("%Y%m%d") if isinstance(trade_date, date) else str(trade_date)
    if not schedule:
        raise ValueError(f"{day} 缺少生效的 MO 交易所保证金参数，请提供 margin_rates")
    effective = max((key for key in schedule if key <= day), default=None)
    if effective is None:
        raise ValueError(f"{day} 早于已提供的 MO 交易所保证金参数生效日")
    return schedule[effective]


def mo_margin_per_contract(
    symbol: str, settle: float, underlying_close: float, adjustment: float, floor: float
) -> float:
    """返回每手人民币金额。settle、underlying_close 和行权价均以指数点计。"""
    match = _MO_CONTRACT.fullmatch(symbol.upper())
    if match is None:
        raise ValueError(f"无法解析 MO 合约代码：{symbol}")
    side, strike_text = match.groups()
    strike = float(strike_text)
    if not all(isfinite(v) for v in (settle, underlying_close, strike, adjustment, floor)):
        raise ValueError(f"{symbol} 保证金输入必须为有限数值")
    if settle < 0 or min(strike, underlying_close, adjustment, floor) <= 0:
        raise ValueError(f"{symbol} 结算价须非负，指数收盘价、行权价及两个系数须为正数")

    # 细则第 34 条。避免 Python round 在恰好半分点时使用偶数舍入。
    underlying_close = float(Decimal(str(underlying_close)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    if side == "C":
        out_of_money = max(strike - underlying_close, 0.0)
        floor_base = underlying_close
    else:
        out_of_money = max(underlying_close - strike, 0.0)
        floor_base = strike

    risk_points = max(underlying_close * adjustment - out_of_money,
                      floor * floor_base * adjustment)
    return MO_MULTIPLIER * (settle + risk_points)


def mo_margin_for_day(data_handler, symbol: str, trade_date: str) -> float:
    """按同一交易日的期权结算、标的现货收盘及交易所参数计算每手保证金。"""
    return mo_margin_per_contract(
        symbol,
        float(data_handler.get_value(symbol, trade_date, "settle")),
        float(data_handler.get_value(symbol, trade_date, "underlying_close")),
        float(data_handler.get_value(symbol, trade_date, "margin_adjustment")),
        float(data_handler.get_value(symbol, trade_date, "minimum_protection")),
    )
