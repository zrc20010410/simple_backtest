from signalhandler.abs_signal_handler import AbsSignalHandler, DEFAULT_SIGNAL_DIR
import pandas as pd
from event import SignalEvent

SIGNAL_COLUMNS = ["datetime", "symbol", "direction", "quantity"]

class SignalHandler(AbsSignalHandler):

    def __init__(self, signals: pd.DataFrame | None = None, update_signals: bool = False):
        super().__init__()
        if update_signals:
            if signals is None:
                raise ValueError("refresh_signals=True 时必须传入 signals")
            self.save_signals_to_csv(signals)

        self.signals = self.read_signals_from_csv()

    @staticmethod
    def save_signals_to_csv(signals: pd.DataFrame):
        path = DEFAULT_SIGNAL_DIR / 'stocks / signals.csv'
        signals.to_csv(path, columns=SIGNAL_COLUMNS, index=False)

    def read_signals_from_csv(self) -> dict[str, list[SignalEvent]]:
        path = self.signal_dir / 'stocks / signals.csv'

        signals: dict[str, list[SignalEvent]] = {}

        data = pd.read_csv(path, dtype={"datetime": str, "symbol": str})
        for row in data.itertuples(index=False):
            signal = SignalEvent(
                datetime=row.datetime,
                symbol=row.symbol,
                direction=row.direction,
                quantity=row.quantity,
            )
            signals.setdefault(row.datetime, []).append(signal)

        return signals