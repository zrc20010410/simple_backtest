from abc import ABC, abstractmethod

class RiskManager(ABC):

    @abstractmethod
    def risk_manager(self, signal):
        raise NotImplementedError("Should implement risk_manager()")