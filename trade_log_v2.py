from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from event import FillEvent, OptionFillEvent as LegacyOptionFillEvent
from event_v2 import OptionFillEvent


@dataclass(frozen=True)
class Trade:
    """一笔已成交的交易记录。"""
    trade_time: str | datetime
    symbol: str
    exchange: str
    direction: str
    quantity: int | float
    fill_price: float
    commission: float
    signal_type: str | None = None

    @property
    def amount(self) -> float:
        """成交金额，不含手续费。"""
        return self.quantity * self.fill_price


class TradeLog:

    def __init__(self, on_fill: Callable[[FillEvent], None]):
        self._on_fill = on_fill
        self.trades: list[Trade] = []

    def record_fill(self, event: FillEvent) -> None:
        if event.type != "FILL":
            raise ValueError("TradeLog 只接受 FILL 事件")

        if isinstance(event, LegacyOptionFillEvent):
            raise TypeError("请使用 event_v2.OptionFillEvent，quantity 传已换算的成交数量")
        trade = Trade(
            trade_time=event.datetime,
            symbol=event.symbol,
            exchange=event.exchange,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=event.fill_price,
            commission=event.commission,
            signal_type=event.signal_type if isinstance(event, OptionFillEvent) else None,
        )

        self._on_fill(event)
        self.trades.append(trade)
