from abc import ABC, abstractmethod
from portfolio.abstract_portfolio import AbstractPortfolio
from event import SignalEvent
class AbstractRiskManager(ABC):

    def __init__(self, portfolio: AbstractPortfolio):
        self.portfolio = portfolio

    @abstractmethod
    def risk_manager(self, signal : SignalEvent):
        raise NotImplementedError("Should implement risk_manager()")