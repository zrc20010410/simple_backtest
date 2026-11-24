from event import OptionFillEvent, OptionSignalEvent
from .abs_execution import ExecutionHandler
from datahandler.options_data_handler import OptionsDataHandler


class OptionsExecutionHandler(ExecutionHandler):

    def __init__(self, events, data_handler: OptionsDataHandler):
        self.events = events
        self.data_handler = data_handler

    def execute_order(self, event: OptionSignalEvent):
        if event.type == 'SIGNAL':
            fill_event = OptionFillEvent(
                event.datetime, event.symbol, 'Test_Exchange', event.quantity, event.direction,
                self.data_handler.get_value(event.symbol, event.datetime, event.fill_time.lower()), event.signal_type,
            )
            self.events.put(fill_event)
