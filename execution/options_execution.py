from event import OptionFillEvent, OptionSignalEvent
from execution.abstract_execution import AbstractExecutionHandler
from datahandler.options_data_handler import OptionsDataHandler
from portfolio.options_portfolio import OptionsPortfolio


class OptionsExecutionHandler(AbstractExecutionHandler):

    def __init__(self, events, data_handler: OptionsDataHandler, portfolio: OptionsPortfolio):
        super().__init__(events, data_handler, portfolio)

    def execute_order(self, event: OptionSignalEvent):

        quantity = event.quantity
        position = self.positions[event.symbol]
        # 可平手数
        closable = max(0, position if event.direction == "SELL" else -position)
        if event.signal_type == "OPEN" and 0 < closable < quantity:
            orders = [("CLOSE", closable), ("OPEN", quantity - closable)]
        else:
            single_type = "CLOSE" if closable > 0 else event.signal_type
            orders = [(single_type, quantity)]

        fill_price = self.data_handler.get_value(event.symbol, event.datetime, event.fill_time.lower())

        for signal_type, fill_quantity in orders:
            fill = OptionFillEvent(
                datetime=event.datetime, symbol=event.symbol, exchange="Test_Exchange",
                quantity=fill_quantity, direction=event.direction, fill_price=fill_price,
                signal_type=signal_type,
            )
            self.events.put(fill)