from backtest.options_backtest import OptionsBacktest
from signalhandler.options_signal_handler import OptionsSignalHandler
from datahandler.options_data_handler import OptionsDataHandler
from portfolio.options_portfolio import OptionsPortfolio
from riskmanager.options_riskmanager import OptionsRiskManager
from execution.options_execution import OptionsExecutionHandler
from trade_log import OptionsTradeLog


def main():
    start_date = '20230101'
    end_date = '20261008'
    plot_performance = True
    print_trade_log = False
    backtest = OptionsBacktest(
        start_date=start_date, end_date=end_date, init_capital=1_000_000,
        signals_handler=OptionsSignalHandler(),
        data_handler=OptionsDataHandler,
        risk_manager=OptionsRiskManager,
        execution_handler=OptionsExecutionHandler,
        portfolio=OptionsPortfolio,
        trade_log=OptionsTradeLog,
        benchmark='000852.SH',
        plot_performance = plot_performance,
        print_trade_log = print_trade_log,
    )
    backtest.run_backtest()


if __name__ == "__main__":
    main()
