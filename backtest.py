import queue
from queue import Empty
from datahandler.abs_data_handler import ABSDataHandler
from datahandler.options_data_handler import OptionsDataHandler
from signal_handler import OptionsSignalHandler, SignalHandler
from portfolio.abs_portfolio import ABSPortfolio
from riskmanager.abs_riskmanager import RiskManager
from execution.abs_execution import ExecutionHandler
from performance import PerformanceReport
from trade_log import OptionTrade, OptionsTradeLog, TradeLog

class Backtest(object):
    """
    回测类
    """
    def __init__(self, start_date, end_date, init_capital,
                 data_handler: type[ABSDataHandler], signals_handler: SignalHandler | OptionsSignalHandler,
                 risk_manager: type[RiskManager], execution_handler: type[ExecutionHandler],
                 portfolio: type[ABSPortfolio], benchmark):
        self.events = queue.Queue()
        self.start_date = start_date
        self.end_date = end_date
        self.init_capital = init_capital

        self.data_handler_cls = data_handler
        self.risk_manager_cls = risk_manager
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio

        self.signals_handler = signals_handler
        self.signals = signals_handler.signals
        self.benchmark = benchmark

    def _create_trading_instances(self):
        """
        实例化所有类:
        """
        self.data_handler = self.data_handler_cls(self.signals_handler.symbol_list, self.start_date, self.end_date)
        self.portfolio = self.portfolio_cls(self.events, self.data_handler, self.start_date, self.init_capital)
        self.trade_log = self._create_trade_log()
        self.risk_manager = self.risk_manager_cls(self.portfolio)
        self.execution_handler = self.execution_handler_cls(self.events, self.data_handler)

    def _create_trade_log(self) -> TradeLog:
        if isinstance(self.data_handler, OptionsDataHandler):
            return OptionsTradeLog(self.portfolio.update_portfolio, self.data_handler.contract_multiplier)
        return TradeLog(self.portfolio.update_portfolio)

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

    def _perform_backtest(self):
        report = PerformanceReport(self.portfolio.history, self.portfolio.init_capital)
        report.print_summary()
        print(report.daily_snapshot)
        report.plot(benchmark=self.benchmark)

    def _print_trade_log(self):
        print(f"本次回测共成交 {len(self.trade_log.trades)} 笔")
        for trade in self.trade_log.trades:
            action = trade.direction
            if isinstance(trade, OptionTrade) and trade.signal_type:
                action = f"{action} {trade.signal_type}"
            print(
                trade.trade_time,
                trade.symbol,
                action,
                trade.quantity,
                trade.fill_price,
                trade.amount,
                f"{trade.commission:.2f}"
            )

    def run_backtest(self):
        self._create_trading_instances()
        self._run_backtest()
        self._perform_backtest()
        self._print_trade_log()

