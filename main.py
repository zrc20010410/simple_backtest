"""从项目根目录运行：python -m src.backtester.main"""

import pandas as pd
from backtest import Backtest
from data_handler import DataHandler
from signal_handler import SignalHandler
from portfolio import Portfolio
from riskmanager.simple_riskmanager import SimpleRiskManager
from execution.simulated_execution import SimulatedExecutionHandler


def main():
    symbol_list = ['000001.SZ', '000011.SZ', '000025.SZ', '600519.SH']
    start_date = '20260101'
    end_date = '20260401'

    signals = pd.DataFrame({
        "datetime": ["20260102", "20260102", "20260102", "20260103", "20260104", "20260105"],
        "symbol": ["000001.SZ", "000011.SZ", "000025.SZ", "000001.SZ", "000001.SZ", "000001.SZ"],
        "signal_type": ["BUY", "BUY", "BUY", "BUY", "SELL", "SELL"],
        "quantity": [100, 100, 100, 300, 200, 200],
    })

    backtest = Backtest(
        symbol_list=symbol_list, start_date=start_date, end_date=end_date,
        init_capital=100_000,
        data_handler=DataHandler,
        signals_handler=SignalHandler(signals),
        risk_manager=SimpleRiskManager,
        execution_handler=SimulatedExecutionHandler,
        portfolio=Portfolio,
        benchmark=None,
    )
    backtest.run_backtest()


if __name__ == "__main__":
    main()
