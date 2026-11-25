from backtest import Backtest
from signal_handler import SignalHandler, OptionsSignalHandler
from datahandler.options_data_handler import OptionsDataHandler
from portfolio.options_portfolio import OptionPortfolio
from riskmanager.options_riskmanager import OptionsRiskManager
from execution.options_execution import OptionsExecutionHandler

def main():
    start_date = '20230101'
    end_date = '20261008'

    backtest = Backtest(
        start_date=start_date, end_date=end_date, init_capital=1_000_000,
        data_handler=OptionsDataHandler,
        signals_handler=OptionsSignalHandler(),
        risk_manager=OptionsRiskManager,
        execution_handler=OptionsExecutionHandler,
        portfolio=OptionPortfolio,
        benchmark='000852.SH',
    )
    backtest.run_backtest()


if __name__ == "__main__":
    main()
