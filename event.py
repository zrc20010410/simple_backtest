from datetime import datetime


class Event(object):
    """
    本类为所有事件的父类。
    """
    pass


class MarketEvent(Event):
    """
    本类为 Market 事件，由 Data 类产生。为从数据源读取的单个时间间隔（time step）的资产价格信息。
    Strategy 类接收 Market 事件。
    """

    def __init__(self):
        self.type = 'MARKET'


class SignalEvent(Event):
    """
    本类为 Signal 事件，由 Strategy 类产生。表现为是否做多、做空或者平仓。
    RiskManager 类接收 Signal 事件。
    """

    def __init__(self, datetime: str, symbol: str, signal_type: str, quantity: int):
        """
        datetime - Signal 产生的时间
        symbol - 交易标的
        signal_type - 'BUY' or 'SELL'
        quantity - 交易数量
        """

        self.type = 'SIGNAL'
        self.symbol = symbol
        self.datetime = datetime
        self.signal_type = signal_type
        self.quantity = quantity


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


def calculate_commission(fill_price: float, quantity: int, direction: str):
    """
    当未传入手续费时, 自动计算出一个手续费
        手续费: 0.01%, 最低5块
        印花税: 0.1%
    """
    min_commission = 5
    commission_rate = 0.0001
    stamp_tax_rate = 0.001

    commission = max(min_commission, commission_rate * (fill_price * quantity))
    stamp_tax = stamp_tax_rate * (fill_price * quantity) if direction == 'SELL' else 0
    total_cost = commission + stamp_tax

    return total_cost
