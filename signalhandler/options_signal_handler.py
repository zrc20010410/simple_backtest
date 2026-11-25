import pandas as pd
from event import OptionSignalEvent
from pathlib import Path
from signalhandler.abs_signal_handler import AbsSignalHandler, DEFAULT_SIGNAL_DIR

OPTION_SIGNAL_COLUMNS = ["datetime", "symbol", "direction", "quantity", "signal_type", "fill_time"]

class OptionsSignalHandler(AbsSignalHandler):
    """读取期权信号，按交易日分组并保留同日记录的顺序。"""
    def __init__(self, path: str | Path | None = None):

        super().__init__()
        self.path = self.signal_dir / "options/signals.csv" if path is None else Path(path)
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