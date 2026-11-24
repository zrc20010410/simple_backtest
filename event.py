from datetime import datetime
from math import isfinite


class Event(object):
    """
    本类为所有事件的父类。
    """
    pass


class SignalEvent(Event):
    """
    本类为 Signal 事件，由 Strategy 类产生。
    RiskManager 类接收 Signal 事件。
    """

    def __init__(self, datetime: str, symbol: str, direction: str, quantity: int, ):
        """
        datetime - Signal 产生的时间
        symbol - 交易标的
        direction - 'BUY' or 'SELL'
        quantity - 交易数量
        val_type - 'OPEN' or 'CLOSE'
        """
        if direction not in ("BUY", "SELL"):
            raise ValueError("signal_type 必须是 BUY 或 SELL")
        self.type = 'SIGNAL'
        self.symbol = symbol
        self.datetime = datetime
        self.direction = direction
        self.quantity = quantity

class OptionSignalEvent(SignalEvent):
    def __init__(self, datetime: str, symbol: str, direction: str, quantity: int, *, signal_type: str, fill_time: str):
        """
        signal_type - 开仓还是平仓 'OPEN' or 'CLOSE'
        fill_time - 交易开盘成交或收盘成交 'OPEN' or 'CLOSE'
        """
        if signal_type and fill_time not in ("OPEN", "CLOSE"):
            raise ValueError("signal_type 和 val_type 必须是 OPEN 或 CLOSE")

        super().__init__(datetime, symbol, direction, quantity)
        self.fill_time = fill_time
        self.signal_type = signal_type


class FillEvent(Event):
    """
    本类为 Fill 事件，由 Execution 类产生，Execution 类模拟交易的结果并产生 Fill 事件。
    Portfolio 类接收 Fill 事件。
    """

    def __init__(self, datetime: datetime, symbol, exchange, quantity,
                 direction, fill_price, commission=None):
        """
        datetime - Fill 的时间
        symbol - 交易标的
        exchange - 交易发生的交易所
        quantity - 交易数量。只能为正
        direction - 'BUY','SELL'
        fill_price - 标的完成交易的价格
        commission - 手续费
        """
        if direction not in ("BUY", "SELL"):
            raise ValueError("direction 必须是 BUY 或 SELL")

        self.type = 'FILL'
        self.datetime = datetime
        self.symbol = symbol
        self.exchange = exchange
        self.quantity = quantity
        self.direction = direction
        self.fill_price = fill_price

        if commission is None:
            self.commission = calculate_commission(self.fill_price, self.quantity, self.direction)
        else:
            self.commission = commission


class OptionFillEvent(FillEvent):
    def __init__(self, datetime, symbol, exchange, quantity, direction, fill_price, *, signal_type: str,
                 commission: float, ):
        if signal_type not in ("OPEN", "CLOSE"):
            raise ValueError("signal_type 必须是 OPEN 或 CLOSE")
        if commission is None or not isfinite(commission):
            raise ValueError("期权成交必须明确提供有效的手续费")
        super().__init__(
            datetime, symbol, exchange, quantity, direction, fill_price,
            commission=commission,
        )
        self.signal_type = signal_type


def calculate_commission(fill_price: float, quantity: int, direction: str):
    """
    当未传入手续费时, 自动计算出一个手续费
        手续费: 0.01%, 最低5块
        印花税: 0.05%
    """
    min_commission = 5
    commission_rate = 0.0001
    stamp_tax_rate = 0.0005

    commission = max(min_commission, commission_rate * (fill_price * quantity))
    stamp_tax = stamp_tax_rate * (fill_price * quantity) if direction == 'SELL' else 0
    total_cost = commission + stamp_tax

    return total_cost
