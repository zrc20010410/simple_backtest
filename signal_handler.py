from pathlib import Path

import pandas as pd
from event import SignalEvent

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[0] / "data"

SIGNAL_COLUMNS = ["datetime", "symbol", "signal_type", "quantity"]


class SignalHandler:

    def __init__(self, signals: pd.DataFrame, refresh_signals: bool = False):

        path = DEFAULT_DATA_DIR / "signals.csv"

        if refresh_signals:
            self.save_signals_to_csv(signals, path)

        self.signals = self.read_signals_from_csv(path)

    @staticmethod
    def save_signals_to_csv(signals: pd.DataFrame, path) -> Path:

        signals.to_csv(path, columns=SIGNAL_COLUMNS, index=False)
        return path

    @staticmethod
    def read_signals_from_csv(path) -> dict[str, list[SignalEvent]]:
        signals: dict[str, list[SignalEvent]] = {}

        data = pd.read_csv(path, dtype={"datetime": str, "symbol": str})
        for row in data.itertuples(index=False):
            signal = SignalEvent(
                datetime=row.datetime,
                symbol=row.symbol,
                signal_type=row.signal_type,
                quantity=row.quantity,
            )
            signals.setdefault(row.datetime, []).append(signal)

        return signals

if __name__ == "__main__":
    signals = pd.DataFrame({
        "datetime": ["20260105", "20260105", "20260105", "20260106", "20260107", "20260108", "20260108", "20260108", ],
        "symbol": ["000001.SZ", "000011.SZ", "000025.SZ", "000001.SZ", "000001.SZ", "000001.SZ", "000011.SZ",
                   "000025.SZ", ],
        "signal_type": ["BUY", "BUY", "BUY", "BUY", "SELL", "SELL", "SELL", "SELL"],
        "quantity": [10000, 10000, 10000, 30000, 20000, 20000, 10000, 10000, ],
    })
    signal_handler = SignalHandler(signals, True)
