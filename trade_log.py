from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from math import isfinite
from event import FillEvent, OptionFillEvent


@dataclass(frozen=True)
class Trade:
    """一笔已成交的交易记录。"""
    trade_time: str | datetime
    symbol: str
    exchange: str
    direction: str
    quantity: int
    fill_price: float
    commission: float

    @property
    def amount(self) -> float:
        """成交金额，不含手续费。"""
        return self.quantity * self.fill_price


@dataclass(frozen=True)
class OptionTrade(Trade):
    contract_multiplier: float
    signal_type: str | None = None  # 兼容手工构造的旧 MOTrade；日志从成交事件填入开平标志。

    @property
    def amount(self) -> float:
        """买卖双方均按正数记录权利金成交额（元），手续费单列。"""
        return round(self.quantity * self.fill_price * self.contract_multiplier, 2)


class TradeLog:

    def __init__(self, on_fill: Callable[[FillEvent], None]):
        self._on_fill = on_fill
        self.trades: list[Trade] = []

    def _make_trade(self, event: FillEvent) -> Trade:
        return Trade(
            trade_time=event.datetime,
            symbol=event.symbol,
            exchange=event.exchange,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=event.fill_price,
            commission=event.commission,
        )

    def record_fill(self, event: FillEvent) -> None:
        if event.type != "FILL":
            raise ValueError("TradeLog 只接受 FILL 事件")
        trade = self._make_trade(event)
        self._on_fill(event)
        self.trades.append(trade)


class OptionsTradeLog(TradeLog):
    def __init__(self, on_fill: Callable[[FillEvent], None], contract_multiplier: float):
        super().__init__(on_fill)
        if not isfinite(contract_multiplier) or contract_multiplier <= 0:
            raise ValueError("期权合约乘数必须为有限正数")
        self.contract_multiplier = contract_multiplier

    def _make_trade(self, event: FillEvent) -> OptionTrade:
        if not isinstance(event, OptionFillEvent):
            raise ValueError("OptionsTradeLog 只接受 OptionFillEvent")
        if event.signal_type not in ("OPEN", "CLOSE"):
            raise ValueError(f"未知的期权开平标志 {event.signal_type!r}")
        return OptionTrade(
            trade_time=event.datetime,
            symbol=event.symbol,
            exchange=event.exchange,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=event.fill_price,
            commission=event.commission,
            contract_multiplier=self.contract_multiplier,
            signal_type=event.signal_type,
        )
