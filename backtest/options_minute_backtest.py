from event import OptionSignalEvent
from options_backtest import OptionsBacktest


class OptionsMinuteBacktest(OptionsBacktest):

    def _run_backtest(self):
        for trade_date in self.data_handler.trade_dates:
            self.data_handler.load_minute_day(trade_date)

            # 第一版约定普通信号当日有效，最后一分钟的信号不隔夜。
            pending_signals = []

            for i, bar_start in enumerate(
                self.data_handler.iter_bar_starts(trade_date)
            ):
                # 1. 上一交易日日终触发的强平，在今天第一根分钟线开盘执行。
                if i == 0 and self.liquidation_status == "PENDING":
                    self._put_liquidation_signals(bar_start)
                    self._execute_signals()

                    if not any(self.portfolio.positions.values()):
                        self.liquidation_status = "LIQUIDATED"

                if self.liquidation_status != "NORMAL":
                    continue

                # 2. 本分钟开盘，执行上一根 K 线收盘后生成的普通信号。
                for signal in pending_signals:
                    order = OptionSignalEvent(
                        datetime=bar_start,
                        symbol=signal.symbol,
                        direction=signal.direction,
                        quantity=signal.quantity,
                        signal_type=signal.signal_type,
                        fill_time="OPEN",
                    )
                    self.events.put(order)
                    self._execute_signals()

                # 3. 本分钟结束，取出基于本根 K 线产生的信号。
                pending_signals = self.signals.get(bar_start, [])

            # 4. 全日分钟线走完后，才执行到期结算、日终估值和强平判断。
            self.portfolio.record_daily_snapshot(trade_date)

            if self.liquidation_status == "NORMAL":
                snapshot = self.portfolio.history[trade_date]

                if round(snapshot.available_cash, 2) < 0:
                    if any(snapshot.positions.values()):
                        self.liquidation_status = "PENDING"
                    else:
                        self.liquidation_status = "HALTED"