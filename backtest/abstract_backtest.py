from abc import ABC, abstractmethod
from queue import Empty, Queue

from datahandler.abstract_data_handler import AbstractDataHandler
from execution.abstract_execution import AbstractExecutionHandler
from performance import PerformanceReport
from portfolio.abstract_portfolio import AbstractPortfolio
from riskmanager.abstract_riskmanager import AbstractRiskManager
from signalhandler.abstract_signal_handler import AbstractSignalHandler
from trade_log import OptionTrade, TradeLog


class AbstractBacktest(ABC):
    def __init__(self, start_date, end_date, init_capital,
                 data_handler: type[AbstractDataHandler], signals_handler: AbstractSignalHandler,
                 risk_manager: type[AbstractRiskManager], execution_handler: type[AbstractExecutionHandler],
                 portfolio: type[AbstractPortfolio], trade_log : type[TradeLog],benchmark, plot_performance: bool, print_trade_log: bool, ):
        self.events = Queue()
        self.start_date = start_date
        self.end_date = end_date
        self.init_capital = init_capital

        self.data_handler_cls = data_handler
        self.risk_manager_cls = risk_manager
        self.execution_handler_cls = execution_handler
        self.portfolio_cls = portfolio
        self.trade_log_cls = trade_log

        self.signals_handler = signals_handler
        self.signals = signals_handler.signals
        self.benchmark = benchmark
        self.plot_performance = plot_performance
        self.print_trade_log = print_trade_log

    def _create_instances(self):
        self.events = Queue()
        self.data_handler = self.data_handler_cls(self.signals_handler.symbol_list, self.start_date, self.end_date)
        self.portfolio = self.portfolio_cls(self.events, self.data_handler, self.start_date, self.init_capital)
        self.trade_log = self.trade_log_cls(self.portfolio.update_portfolio)
        self.risk_manager = self.risk_manager_cls(self.portfolio)
        self.execution_handler = self.execution_handler_cls(self.events, self.data_handler, self.portfolio)

    @abstractmethod
    def _run_backtest(self):
        """按回测频率推进时间，处理交易并记录账户快照。"""
        ...

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
                trade.trade_time, trade.symbol, action, trade.quantity,
                trade.fill_price, trade.amount, f"{trade.commission:.2f}",
            )

    def run_backtest(self):
        self._create_trading_instances()
        self._run_backtest()
        if self.plot_performance:
            self._perform_backtest()
        if self.print_trade_log:
            self._print_trade_log()
