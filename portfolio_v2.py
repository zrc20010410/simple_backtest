from abc import ABC, abstractmethod
from dataclasses import dataclass
from math import isclose, isfinite

from datahandler.data_handler import DataHandler
from event import FillEvent, OptionFillEvent as LegacyOptionFillEvent
from event_v2 import OptionFillEvent
from mo_margin_v2 import mo_margin_for_day
from portfolio.portfolio import Snapshot


class BasePortfolio(ABC):
    """账户公共状态。equity 和 market_values 表示最近一次收盘结果。"""

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):
        self.events = events
        self.data_handler = data_handler
        self.start_date = start_date
        self.init_capital = init_capital
        self.cash = init_capital
        self.total_commission = 0.0
        self.history: dict[str, Snapshot] = {}

    @property
    def market_values(self) -> dict[str, float]:
        if not self.history:
            return dict.fromkeys(self.data_handler.symbol_list, 0.0)
        return next(reversed(self.history.values())).market_values.copy()

    @property
    def equity(self) -> float:
        if not self.history:
            return self.init_capital
        return next(reversed(self.history.values())).equity

    @property
    def available_cash(self) -> float:
        return self.cash

    def _book_fill_cash(self, signed_amount: float, commission: float) -> None:
        """买入的成交金额为正，卖出的成交金额为负。"""
        self.cash -= signed_amount + commission
        self.total_commission += commission

    @abstractmethod
    def update_portfolio(self, event: FillEvent) -> None:
        """按已经成交的事件更新账户。"""

    @abstractmethod
    def record_daily_snapshot(self, trade_date: str) -> None:
        """用当日的估值及结算数据记录独立快照。"""


class Portfolio(BasePortfolio):
    """现货股票账户，持仓单位为股。"""

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):
        super().__init__(events, data_handler, start_date, init_capital)
        self.positions: dict[str, int] = dict.fromkeys(data_handler.symbol_list, 0)

    def update_portfolio(self, event: FillEvent) -> None:
        if event.type != "FILL":
            return
        if isinstance(event, (OptionFillEvent, LegacyOptionFillEvent)):
            raise TypeError("期权成交需要使用 OptionPortfolio")
        quantity = event.quantity if event.direction == "BUY" else -event.quantity
        self.positions[event.symbol] += quantity
        self._book_fill_cash(quantity * event.fill_price, event.commission)

    def record_daily_snapshot(self, trade_date: str) -> None:
        market_values = dict.fromkeys(self.positions, 0.0)
        for symbol, quantity in self.positions.items():
            if quantity:
                close = self.data_handler.get_valuation_close(symbol, trade_date)
                market_values[symbol] = quantity * close
        self.history[trade_date] = Snapshot(
            positions=self.positions.copy(),
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
        )


@dataclass
class OptionSnapshot(Snapshot):
    """positions 记录每个合约的张数，正数为多仓，负数为空仓。"""

    margin_used: float
    available_cash: float


class OptionPortfolio(BasePortfolio):
    """权利金收付型期权账户，保证金由行情源按每张义务仓提供。

    成交数量已含乘数；用当日 multiplier 换回持仓张数，权利金直接按成交数量计算。
    get_value(symbol, date, field) 在增加义务仓时提供 open_margin_per_contract
    （开仓时已知）。MO 义务仓按中金所日终公式计提；其他品种读取 margin_per_contract。
    保证金按独立合约计提，不含组合抵扣或备兑证券。
    """

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):
        super().__init__(events, data_handler, start_date, init_capital)
        self.positions: dict[str, int] = dict.fromkeys(data_handler.symbol_list, 0)
        self._margin_by_symbol = dict.fromkeys(self.positions, 0.0)

    @property
    def margin_used(self) -> float:
        return sum(self._margin_by_symbol.values())

    @property
    def available_cash(self) -> float:
        return self.cash - self.margin_used

    def _market_field(self, symbol, trade_date, field: str) -> float:
        raw = self.data_handler.get_value(symbol, trade_date, field)
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{symbol} 在 {trade_date} 的 {field} 无效：{raw!r}") from exc
        if not isfinite(value) or value < 0 or (field == "multiplier" and value == 0):
            raise ValueError(f"{symbol} 在 {trade_date} 的 {field} 无效：{raw!r}")
        return value

    def update_portfolio(self, event: FillEvent) -> None:
        if event.type != "FILL":
            return
        if not isinstance(event, OptionFillEvent):
            raise TypeError("请使用 event_v2.OptionFillEvent，quantity 传已换算的成交数量")
        old = self.positions[event.symbol]
        if event.direction not in ("BUY", "SELL") or event.signal_type not in ("OPEN", "CLOSE"):
            raise ValueError(f"无效期权成交方向或开平标志：{event.direction} {event.signal_type}")
        multiplier = self._market_field(event.symbol, event.datetime, "multiplier")
        contracts = event.quantity / multiplier
        qty = round(contracts)
        if qty <= 0 or not isclose(contracts, qty, rel_tol=0, abs_tol=1e-9):
            raise ValueError(f"{event.symbol} 的成交数量 {event.quantity} 无法按乘数 {multiplier} 换算为整张")
        change = qty if event.direction == "BUY" else -qty
        if event.signal_type == "OPEN":
            if (old > 0 and change < 0) or (old < 0 and change > 0):
                raise ValueError(f"{event.symbol} 反向开仓前须先平仓")
        elif event.direction == "BUY" and qty > -old:
            raise ValueError(f"{event.symbol} 可平义务仓不足")
        elif event.direction == "SELL" and qty > old:
            raise ValueError(f"{event.symbol} 可平权利仓不足")
        new = old + change
        if not isfinite(event.fill_price) or event.fill_price < 0:
            raise ValueError("期权成交价格必须是有限非负数")

        margin = self._margin_by_symbol[event.symbol]
        if new < 0 and new < old:
            per_contract = self._market_field(event.symbol, event.datetime, "open_margin_per_contract")
            margin += qty * per_contract
        elif old < 0 and new > old:
            margin *= abs(new) / abs(old)

        premium = event.quantity * event.fill_price
        self._book_fill_cash(premium if event.direction == "BUY" else -premium, event.commission)
        self.positions[event.symbol] = new
        self._margin_by_symbol[event.symbol] = margin

    def record_daily_snapshot(self, trade_date: str) -> None:
        market_values = dict.fromkeys(self.positions, 0.0)
        margins = dict.fromkeys(self.positions, 0.0)
        for symbol, position in self.positions.items():
            if position:
                price = self._market_field(symbol, trade_date, "settle")
                multiplier = self._market_field(symbol, trade_date, "multiplier")
                market_values[symbol] = position * price * multiplier
            if position < 0:
                if symbol.upper().startswith("MO"):
                    per_contract = mo_margin_for_day(self.data_handler, symbol, trade_date)
                else:
                    per_contract = self._market_field(symbol, trade_date, "margin_per_contract")
                margins[symbol] = abs(position) * per_contract

        margin_used = sum(margins.values())
        snapshot = OptionSnapshot(
            positions=self.positions.copy(),
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
            margin_used=margin_used,
            available_cash=self.cash - margin_used,
        )
        self._margin_by_symbol = margins
        self.history[trade_date] = snapshot
