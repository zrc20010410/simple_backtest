import re
from math import isfinite
from numbers import Integral

from config import FEE_PER_CONTRACT
from utils.commission import Commission

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
        """
        if direction not in ("BUY", "SELL"):
            raise ValueError("signal_type 必须是 BUY 或 SELL")
        if isinstance(quantity, bool) or not isinstance(quantity, Integral) or quantity <= 0:
            raise ValueError("quantity必须为正整数")

        self.type = 'SIGNAL'
        self.symbol = symbol
        self.datetime = datetime
        self.direction = direction
        self.quantity = quantity


class OptionSignalEvent(SignalEvent):
    def __init__(self, datetime: str, symbol: str, direction: str, quantity: int, *, signal_type: str, fill_time: str):
        """
        signal_type - 开仓还是平仓 'OPEN' or 'CLOSE'
        fill_time - 交易时间，如"0930"、"1500"
        """
        if signal_type not in ("OPEN", "CLOSE"):
            raise ValueError("signal_type 必须是 OPEN 或 CLOSE")

        if (not isinstance(fill_time, str)
                or not re.fullmatch(r"(?:[01][0-9]|2[0-3])[0-5][0-9]", fill_time)
                or not ("0930" <= fill_time <= "1130" or "1300" <= fill_time <= "1500")):
            raise ValueError("fill_time 必须在交易时段内，例如 '0930' 或 '1500'")
        super().__init__(datetime, symbol, direction, quantity)
        self.fill_time = fill_time
        self.signal_type = signal_type

class FillEvent(Event):
    """
    本类为 Fill 事件，由 Execution 类产生，Execution 类模拟交易的结果并产生 Fill 事件。
    Portfolio 类接收 Fill 事件。
    """

    def __init__(self, datetime: str, symbol, exchange, quantity,
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
            commission = Commission.stock_commission(fill_price, quantity, direction)
        self.commission = commission


class OptionFillEvent(FillEvent):
    def __init__(self, datetime: str, symbol: str, exchange, quantity: int, direction: str, fill_price: float,
                 signal_type: str, commission: float | None = None, fee_per_contract: float | None = None):

        if commission is None:
            if fee_per_contract is None:
                if not symbol.upper().startswith("MO"):
                    raise ValueError(f"请提供 {symbol} 的每手手续费或本笔总手续费")
                fee_per_contract = FEE_PER_CONTRACT
            commission = int(quantity) * fee_per_contract
        if not isfinite(commission) or commission < 0:
            raise ValueError("期权手续费必须是有限非负数")

        super().__init__(
            datetime, symbol, exchange, quantity, direction, fill_price, commission=commission,
        )
        self.signal_type = signal_type


