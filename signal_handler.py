from pathlib import Path
import pandas as pd
from event import OptionSignalEvent, SignalEvent

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[0] / "data"
DEFAULT_SIGNAL_DIR = DEFAULT_DATA_DIR / "signals"
SIGNAL_COLUMNS = ["datetime", "symbol", "direction", "quantity"]
OPTION_SIGNAL_COLUMNS = ["datetime", "symbol", "direction", "quantity", "signal_type", "fill_time"]

class SignalHandler:

    def __init__(self, signals: pd.DataFrame | None = None, update_signals: bool = False):
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
        path = DEFAULT_SIGNAL_DIR / 'stocks / signals.csv'

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

class OptionsSignalHandler:
    """读取期权信号，按交易日分组并保留同日记录的顺序。"""
    def __init__(self, path: str | Path | None = None):
        self.path = DEFAULT_SIGNAL_DIR / "options/signals.csv" if path is None else Path(path)
        self.signals = self.read_signals_from_csv()

        self.symbol_list: list[str] = sorted({
            signal.symbol
            for daily_signals in self.signals.values()
            for signal in daily_signals
        })

    def read_signals_from_csv(self) -> dict[str, list[OptionSignalEvent]]:
        data = pd.read_csv(
            self.path, usecols=OPTION_SIGNAL_COLUMNS,
            dtype={"datetime": str, "symbol": str},
        )

        if data.isna().any().any():
            raise ValueError(f"{self.path.name} 的期权信号含有缺失字段值")
        dates = data["datetime"].str.replace("-", "", regex=False)
        data["datetime"] = pd.to_datetime(dates, format="%Y%m%d").dt.strftime("%Y%m%d")

        signals: dict[str, list[OptionSignalEvent]] = {}
        for row in data.itertuples(index=False):
            signal = OptionSignalEvent(
                datetime=row.datetime, symbol=row.symbol, direction=row.direction,
                quantity=row.quantity, signal_type=row.signal_type, fill_time=row.fill_time,
            )
            signals.setdefault(signal.datetime, []).append(signal)
        return signals

if __name__ == "__main__":
    signals = pd.DataFrame({
        "datetime": ["20260105", "20260105", "20260105", "20260106", "20260107", "20260108", "20260108", "20260108", ],
        "symbol": ["000001.SZ", "000011.SZ", "000025.SZ", "000001.SZ", "000001.SZ", "000001.SZ", "000011.SZ",
                   "000025.SZ", ],
        "direction": ["BUY", "BUY", "BUY", "BUY", "SELL", "SELL", "SELL", "SELL"],
        "quantity": [10000, 10000, 10000, 30000, 20000, 20000, 10000, 10000, ],
    })
    signal_handler = SignalHandler(signals, True)
