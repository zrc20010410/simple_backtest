from event import FillEvent, SignalEvent
from execution.abstract_execution import AbstractExecutionHandler
from datahandler.stocks_data_handler import DataHandler
from portfolio.stocks_portfolio import StocksPortfolio


class StocksExecutionHandler(AbstractExecutionHandler):

    def __init__(self, events, data_handler: DataHandler, portfolio: StocksPortfolio):
        super().__init__(events, data_handler, portfolio)

    def execute_order(self, event : SignalEvent):
        if event.type == 'SIGNAL':
            fill_event = FillEvent(
                event.datetime, event.symbol,'Test_Exchange', event.quantity, event.direction,
                self.data_handler.get_value(event.symbol,event.datetime,  "open")
            )
            self.events.put(fill_event)
