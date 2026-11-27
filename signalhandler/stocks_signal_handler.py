import pandas as pd
from event import SignalEvent
from config import DEFAULT_SIGNAL_DIR
from signalhandler.abstract_signal_handler import AbstractSignalHandler

SIGNAL_COLUMNS = ["datetime", "symbol", "direction", "quantity"]

class StocksSignalHandler(AbstractSignalHandler):

    path = DEFAULT_SIGNAL_DIR / 'stocks' / 'signals.csv'

    def __init__(self):
        super().__init__()
        self.signals = self.read_signals_from_csv()
        self.symbol_list = self._get_symbol_list()

    @staticmethod
    def save_signals_to_csv(signals: pd.DataFrame):
        path = DEFAULT_SIGNAL_DIR / 'stocks' / 'signals.csv'
        signals.to_csv(path, columns=SIGNAL_COLUMNS, index=False)

    def read_signals_from_csv(self) -> dict[str, list[SignalEvent]]:
        signals: dict[str, list[SignalEvent]] = {}
        data = pd.read_csv(self.path, dtype={"datetime": str, "symbol": str})
        for row in data.itertuples(index=False):
            signal = SignalEvent(
                datetime=row.datetime,
                symbol=row.symbol,
                direction=row.direction,
                quantity=row.quantity,
            )
            signals.setdefault(row.datetime, []).append(signal)

        return signals

    def _get_symbol_list(self) -> list[str]:
        return []
