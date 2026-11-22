from abc import ABC, abstractmethod

class ExecutionHandler(ABC):

    @abstractmethod
    def execute_order(self, event):
        raise NotImplementedError("Should implement execute_order()")
