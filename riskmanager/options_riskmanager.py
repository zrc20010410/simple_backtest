from math import isfinite
from numbers import Integral, Real

from event import OptionSignalEvent
from portfolio.options_portfolio import OptionPortfolio
from .abs_riskmanager import RiskManager


class OptionsRiskManager(RiskManager):
    def __init__(self, portfolio: OptionPortfolio):
        super().__init__(portfolio)

    def risk_manager(self, signal: OptionSignalEvent) -> str | None:
        """校验信号、净持仓和成交时点的报价。通过返回 None，拒绝返回原因。"""
        symbol, direction, quantity = signal.symbol, signal.direction, signal.quantity
        if symbol not in self.portfolio.positions:
            return f"{symbol} 不在回测期权池内"
        if direction not in ("BUY", "SELL"):
            return "买卖方向须为 BUY 或 SELL"
        if signal.signal_type not in ("OPEN", "CLOSE"):
            return "开平标志须为 OPEN 或 CLOSE"
        if signal.fill_time not in ("OPEN", "CLOSE"):
            return "成交时点须为 OPEN 或 CLOSE"
        if isinstance(quantity, bool) or not isinstance(quantity, Integral) or quantity <= 0:
            return "期权手数必须为正整数"

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
