from math import isfinite
from numbers import Integral, Real
from .abs_riskmanager import RiskManager
from portfolio.portfolio import Portfolio
from event import SignalEvent, calculate_commission

class SimpleRiskManager(RiskManager):
    def __init__(self, portfolio: Portfolio):
        self.portfolio = portfolio

    def risk_manager(self, signal: SignalEvent) -> str | None:
        symbol, direction, quantity = signal.symbol, signal.direction, signal.quantity
        if symbol not in self.portfolio.positions:
            return "股票不在回测股票池内"
        if direction not in ("BUY", "SELL"):
            return "无效的买卖方向"
        if isinstance(quantity, bool) or not isinstance(quantity, Integral) or quantity <= 0:
            return "股数必须为正整数"
        if direction == "SELL" and quantity > self.portfolio.positions[symbol]:
            return "持仓不足"

        try:
            price = self.portfolio.data_handler.get_value(symbol, signal.datetime, "open")
        except (KeyError, ValueError) as exc:
            return str(exc.args[0])
        if not isinstance(price, Real) or not isfinite(price) or price <= 0:
            return "当日开盘价无效"

        amount = quantity * price
        commission = calculate_commission(price, quantity, direction)
        cash_needed = commission + (amount if direction == "BUY" else -amount)
        if cash_needed > self.portfolio.cash:
            return f"现金不足：需 {cash_needed:,.2f} 元，可用 {self.portfolio.cash:,.2f} 元"

        return None
