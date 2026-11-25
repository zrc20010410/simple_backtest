from abc import ABC, abstractmethod
from datahandler.abs_data_handler import ABSDataHandler

class ExecutionHandler(ABC):

    def __init__(self, events, data_handler: ABSDataHandler):
        self.events = events
        self.data_handler = data_handler

    @abstractmethod
    def execute_order(self, event):
        raise NotImplementedError("Should implement execute_order()")
