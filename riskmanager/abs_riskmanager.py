from abc import ABC, abstractmethod
from portfolio.abs_portfolio import ABSPortfolio

class RiskManager(ABC):

    def __init__(self, portfolio: ABSPortfolio):
        self.portfolio = portfolio

    @abstractmethod
    def risk_manager(self, signal):
        raise NotImplementedError("Should implement risk_manager()")