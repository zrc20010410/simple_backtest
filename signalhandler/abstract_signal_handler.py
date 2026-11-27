from abc import ABC, abstractmethod
from event import SignalEvent
from collections.abc import Mapping, Sequence

class AbstractSignalHandler(ABC):

    def __init__(self):
        self.signals : Mapping[str, Sequence[SignalEvent]] = {}
        self.symbol_list: list[str] = []

    @abstractmethod
    def read_signals_from_csv(self) -> Mapping[str, Sequence[SignalEvent]]:
        ...

    def _get_symbol_list(self) -> list[str]:
        ...