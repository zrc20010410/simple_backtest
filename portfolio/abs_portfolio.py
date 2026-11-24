from abc import ABC, abstractmethod

from datahandler.data_handler import DataHandler
from event import FillEvent
from portfolio.portfolio import Snapshot

class ABSPortfolio(ABC):
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

    @abstractmethod
    def update_portfolio(self, event: FillEvent) -> None:
        """按已经成交的事件更新账户。"""

    @abstractmethod
    def record_daily_snapshot(self, trade_date: str) -> None:
        """用当日的估值及结算数据记录独立快照。"""