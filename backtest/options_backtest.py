from event import OptionSignalEvent
from queue import Empty

from backtest.abstract_backtest import AbstractBacktest
from datahandler.options_data_handler import OptionsDataHandler
from execution.options_execution import OptionsExecutionHandler
from portfolio.options_portfolio import OptionsPortfolio
from riskmanager.options_riskmanager import OptionsRiskManager
from signalhandler.options_signal_handler import OptionsSignalHandler
from trade_log import OptionsTradeLog

class OptionsBacktest(AbstractBacktest):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.liquidation_status: str = "NORMAL"

    def _create_instances(self):
        super()._create_trading_instances()


    def _create_trade_log(self) -> OptionsTradeLog:
        return OptionsTradeLog( self.portfolio.update_portfolio, self.data_handler.contract_multiplier,)

    def _run_backtest(self):
        """
        回测主循环
        """
        for trade_date in self.data_handler.trade_dates:
            if self.liquidation_status == 'NORMAL':
                for signal in self.signals.get(trade_date, []):
                    self.events.put(signal)
                    self._execute_signals()
            elif self.liquidation_status == 'PENDING':
                self._put_liquidation_signals(trade_date)
                self._execute_signals()
                if not any(self.portfolio.positions.values()):
                    self.liquidation_status = "LIQUIDATED"

            # 每天交易结束
            self.portfolio.record_daily_snapshot(trade_date)

            if self.liquidation_status == 'NORMAL':
                snapshot = self.portfolio.history[trade_date]
                if round(snapshot.available_cash, 2) < 0:
                    if not any(snapshot.positions.values()):
                        self.liquidation_status = "HALTED"
                        action = "已无持仓可平，停止接受策略信号"
                    else:
                        self.liquidation_status = "PENDING"
                        if trade_date == self.data_handler.trade_dates[-1]:
                            action = "回测已结束，强平待执行"
                        else:
                            action = "已触发强平，等待下一交易日开盘生成平仓单"
                    print(f"{trade_date} 日终可用资金 {snapshot.available_cash:,.2f} 元，{action}。")

    def _execute_signals(self):
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
                    print(
                        f"无效订单 {event.datetime} {event.symbol} {action} 数量 {event.quantity}：{reason}")
            elif event.type == "FILL":
                self.trade_log.record_fill(event)

    def _put_liquidation_signals(self, trade_date: str) -> None:
        for symbol, quantity in self.portfolio.positions.items():
            if quantity == 0:
                continue
            self.events.put(OptionSignalEvent(
                trade_date, symbol, "SELL" if quantity > 0 else "BUY", abs(quantity),
                signal_type="CLOSE", fill_time="OPEN",
            ))