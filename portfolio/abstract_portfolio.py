from abc import ABC, abstractmethod
from dataclasses import dataclass
from datahandler.abstract_data_handler import AbstractDataHandler
from event import FillEvent

@dataclass
class Snapshot:
    """单个交易日的账户快照。"""
    positions: dict[str, int]
    market_values: dict[str, float]
    cash: float
    total_commission: float
    equity: float

class AbstractPortfolio(ABC):
    """账户公共状态。equity 和 market_values 表示最近一次收盘结果。"""

    def __init__(self, events, data_handler: AbstractDataHandler, start_date, init_capital):
        self.events = events
        self.data_handler = data_handler
        self.start_date = start_date
        self.init_capital = init_capital
        self.cash = init_capital
        self.total_commission = 0.0
        self.positions = dict.fromkeys(data_handler.symbol_list, 0)
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

    @abstractmethod
    def update_portfolio(self, event: FillEvent) -> None:
        """按已经成交的事件更新账户。"""

    @abstractmethod
    def record_daily_snapshot(self, trade_date: str) -> None:
        """用当日的估值及结算数据记录独立快照。"""
