from abc import ABC, abstractmethod
from event import SignalEvent
from pathlib import Path

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_SIGNAL_DIR = DEFAULT_DATA_DIR / "signals"

class AbsSignalHandler(ABC):

    def __init__(self):
        self.signal_dir = DEFAULT_SIGNAL_DIR

    @abstractmethod
    def read_signals_from_csv(self) -> dict[str, list[SignalEvent]]:
        ...