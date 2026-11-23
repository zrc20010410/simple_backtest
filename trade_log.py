from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from event import FillEvent


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


class TradeLog:

    def __init__(self, on_fill: Callable[[FillEvent], None]):
        self._on_fill = on_fill
        self.trades: list[Trade] = []

    def record_fill(self, event: FillEvent) -> None:
        if event.type != "FILL":
            raise ValueError("TradeLog 只接受 FILL 事件")

        trade = Trade(
            trade_time=event.datetime,
            symbol=event.symbol,
            exchange=event.exchange,
            direction=event.direction,
            quantity=event.quantity,
            fill_price=event.fill_price,
            commission=event.commission,
        )

        self._on_fill(event)
        self.trades.append(trade)