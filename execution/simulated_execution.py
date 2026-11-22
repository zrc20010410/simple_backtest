from ..event import FillEvent
from .abs_execution import ExecutionHandler
from data_handler import DataHandler


class SimulatedExecutionHandler(ExecutionHandler):

    def __init__(self, events, data_handler: DataHandler):
        self.events = events
        self.data_handler = data_handler

    def execute_order(self, event):
        if event.type == 'SIGNAL':
            fill_event = FillEvent(
                event.datetime, event.symbol,'Test_Exchange', event.quantity, event.direction,
                self.data_handler.get_value(event.symbol,event.datetime,  "open")
            )
            self.events.put(fill_event)
