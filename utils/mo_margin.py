from decimal import Decimal
from math import isfinite


def mo_margin_per_contract(
        *, option_type: str, strike: float, settle: float, index_close: float,
        multiplier: float, a: float, b: float,
) -> float:
    """
    :param option_type: 看涨或看跌 "C" or "P"
    :param strike: 合约的行权价
    :param settle: 结算价
    :param index_close: 指数收盘价
    :param multiplier: 合约乘数
    :param a: 保证金调整系数，0.12
    :param b: 最低保障系数，0.5
    """
    if option_type not in ("C", "P"):
        raise ValueError(f"期权类型应为 C 或 P，收到 {option_type!r}")
    if not all(isfinite(v) for v in (strike, settle, index_close, multiplier, a, b)):
        raise ValueError("保证金公式的输入必须是有限数值")
    if settle < 0 or min(strike, index_close, multiplier, a, b) <= 0:
        raise ValueError("结算价须非负，行权价、指数收盘价、乘数和保证金系数须为正")

    index_price = Decimal(str(index_close))
    strike_price = Decimal(str(strike))
    settle = Decimal(str(settle))
    multiplier = Decimal(str(multiplier))
    a = Decimal(str(a))
    b = Decimal(str(b))
    '''
    # Call（看涨期权）
    call_margin = 100 * (call_settle + max(a * S - max(K - S, 0), b * a * S))
    # Put（看跌期权）
    put_margin  = 100 * (put_settle  + max(a * S - max(S - K, 0), b * a * K))
    '''

    if option_type == "C":
        out_of_money = max(strike_price - index_price, 0)
        floor_base = index_price
    else:
        out_of_money = max(index_price - strike_price, 0)
        floor_base = strike_price

    risk_points = max(a * index_price - out_of_money,
                      a * b * floor_base)
    margin_per_contract = multiplier * (settle + risk_points)
    return float(margin_per_contract)
