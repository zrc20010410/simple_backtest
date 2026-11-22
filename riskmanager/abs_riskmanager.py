from abc import ABC, abstractmethod

class RiskManager(ABC):

    @abstractmethod
    def generate_order(self, signal):
        raise NotImplementedError("Should implement generate_order()")

    @abstractmethod
    def update_signal(self, event):
        raise NotImplementedError("Should implement update_signal()")