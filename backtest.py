import queue
from queue import Empty
from data_handler import DataHandler
from signal_handler import SignalHandler
from portfolio import Portfolio
from riskmanager.simple_riskmanager import SimpleRiskManager
from execution.simulated_execution import SimulatedExecutionHandler


class Backtest(object):
    """
    回测类
    """

    def __init__(self, symbol_list, start_date, end_date, init_capital,
                 data_handler: type[DataHandler], signals_handler : SignalHandler,
                 risk_manager: type[SimpleRiskManager], execution_handler: type[SimulatedExecutionHandler],
                 portfolio: type[Portfolio], benchmark):
        self.symbol_list = symbol_list
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
        self.events = queue.Queue()

        self._create_trading_instances()

    def _create_trading_instances(self):
        """
        实例化所有类:
        """
        self.data_handler = self.data_handler_cls(self.symbol_list, self.start_date, self.end_date)
        self.portfolio = self.portfolio_cls(self.events, self.data_handler, self.start_date, self.init_capital)
        self.risk_manager = self.risk_manager_cls(self.events, self.data_handler, self.portfolio)
        self.execution_handler = self.execution_handler_cls(self.events, self.data_handler)

    def _run_backtest(self):
        """
        回测主循环
        """
        for trade_date, daily_signals in sorted(self.signals.items()):
            for signal in daily_signals:
                self.events.put(signal)

            while True:
                try:
                    event = self.events.get_nowait()
                except Empty:
                    break

                if event.type == "SIGNAL":
                    self.execution_handler.execute_signal(event)
                elif event.type == "FILL":
                    self.portfolio.update_fill(event)

    def run_backtest(self):
        self._run_backtest()
