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
    end_date = '20260201'

    signals = pd.DataFrame({
        "datetime": ["20260105", "20260105", "20260105", "20260106", "20260107", "20260108", "20260108", "20260108", ],
        "symbol": ["000001.SZ", "000011.SZ", "000025.SZ", "000001.SZ", "000001.SZ", "000001.SZ", "000011.SZ",
                   "000025.SZ", ],
        "signal_type": ["BUY", "BUY", "BUY", "BUY", "SELL", "SELL", "SELL", "SELL"],
        "quantity": [10000, 10000, 10000, 30000, 20000, 20000, 10000, 10000, ],
    })

    backtest = Backtest(
        symbol_list=symbol_list, start_date=start_date, end_date=end_date,
        init_capital=500000,
        data_handler=DataHandler,
        signals_handler=SignalHandler(signals,True),
        risk_manager=SimpleRiskManager,
        execution_handler=SimulatedExecutionHandler,
        portfolio=Portfolio,
        benchmark='399300.SZ',
    )
    backtest.run_backtest()


if __name__ == "__main__":
    main()
