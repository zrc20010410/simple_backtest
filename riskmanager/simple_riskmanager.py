"""固定买入 100 股，按实际持仓平仓的只做多风控。"""

from .abs_riskmanager import RiskManager
from ..event import OrderEvent, calculate_commission
from data_handler import TushareDataHandler
from ..portfolio import Portfolio

class SimpleRiskManager(RiskManager):
    def __init__(self, events, data_handler : TushareDataHandler,  portfolio :Portfolio):
        self.events = events
        self.portfolio = portfolio
        self.data = data_handler
        self._budget_day = None
        self._remaining_cash = 0

    def generate_order(self, signal):
        """返回候选订单和需要预留的现金；未通过检查时返回空订单。"""
        if signal.type != "SIGNAL":
            return None, 0

        datetime, symbol = signal.datetime, signal.symbol
        cash = self.portfolio.cash
        position = self.portfolio.positions[symbol]

        quantity = 100
        close = self.data.get_latest_bars_values(symbol, "close")[-1]
        cost = quantity * close + calculate_commission(close, quantity, 'BUY')

        if signal.signal_type == "EXIT" and position > 0:
            return OrderEvent(datetime, symbol, position, "SELL"), cost

        if signal.signal_type == "LONG" and position == 0:
            if datetime == self._budget_day:
                cash = min(cash, self._remaining_cash)
            if cash >= cost:
                return OrderEvent(datetime, symbol, quantity, "BUY"), cost

        return None, 0

    def update_signal(self, event):
        """将通过风控的订单入队，并预留当日买入资金。"""
        order, cost = self.generate_order(event)
        if order is None:
            return
        if order.datetime != self._budget_day:
            self._budget_day = order.datetime
            self._remaining_cash = self.portfolio.cash
        self.events.put(order)
        self._remaining_cash -= cost

