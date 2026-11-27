from math import isfinite
from numbers import Integral, Real

from event import OptionSignalEvent, SignalEvent
from portfolio.options_portfolio import OptionsPortfolio
from .abstract_riskmanager import AbstractRiskManager
from config import FEE_PER_CONTRACT
from utils.mo_margin import mo_margin_per_contract

class OptionsRiskManager(AbstractRiskManager):
    def __init__(self, portfolio: OptionsPortfolio):
        super().__init__(portfolio)

    def risk_manager(self, signal: SignalEvent) -> str | None:
        """校验信号、净持仓和成交时点的报价。通过返回 None，拒绝返回原因。"""
        if not isinstance(signal, OptionSignalEvent):
            raise TypeError("OptionPortfolio 需要 OptionFillEvent")

        symbol, direction, quantity = signal.symbol, signal.direction, signal.quantity

        if symbol not in self.portfolio.positions:
            return f"{symbol} 不在回测期权池内"

        if signal.signal_type == "CLOSE":
            position = self.portfolio.positions[symbol]
            closable = max(0, -position if direction == "BUY" else position)
            if quantity > closable:
                return f"可平持仓不足：可平 {closable} 手，申请 {quantity} 手"

        try:
            price = self.portfolio.data_handler.get_value(symbol, signal.datetime, signal.fill_time.lower())
        except (KeyError, ValueError) as exc:
            return str(exc.args[0])
        if isinstance(price, bool) or not isinstance(price, Real) or not isfinite(price) or price <= 0:
            return f"{symbol} 的成交报价须为有限正数"

        return None