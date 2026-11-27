from queue import Empty, Queue

from backtest.abstract_backtest import AbstractBacktest

class StocksBacktest(AbstractBacktest):
    """
    回测类
    """
    def _run_backtest(self):
        """
        回测主循环
        """
        for trade_date in self.data_handler.trade_dates:
            for signal in self.signals.get(trade_date, []):
                self.events.put(signal)
                while True:
                    try:
                        event = self.events.get_nowait()
                    except Empty:
                        break
                    if event.type == "SIGNAL":
                        reason = self.risk_manager.risk_manager(event)
                        if reason is None:
                            self.execution_handler.execute_order(event)
                        else:
                            action = getattr(event, "signal_type", event.direction)
                            print(f"无效订单 {event.datetime} {event.symbol} {action} 数量 {event.quantity}：{reason}")
                    elif event.type == "FILL":
                        self.trade_log.record_fill(event)
            # 每天交易结束
            self.portfolio.record_daily_snapshot(trade_date)
