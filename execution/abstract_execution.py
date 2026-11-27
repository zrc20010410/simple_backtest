from abc import ABC, abstractmethod
from datahandler.abstract_data_handler import AbstractDataHandler
from portfolio.abstract_portfolio import AbstractPortfolio

class AbstractExecutionHandler(ABC):

    def __init__(self, events, data_handler: AbstractDataHandler, portfolio: AbstractPortfolio):
        self.events = events
        self.data_handler = data_handler
        self.positions = portfolio.positions

    @abstractmethod
    def execute_order(self, event):
        raise NotImplementedError("Should implement execute_order()")
