from datahandler.data_handler import DataHandler
from event import FillEvent
from portfolio.abs_portfolio import ABSPortfolio, Snapshot

class Portfolio(ABSPortfolio):

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):

        super().__init__(events, data_handler, start_date, init_capital)


    @property
    def market_values(self) -> dict[str, float]:
        """返回最近一次收盘时各标的的市值，首次收盘前均为零。"""
        if not self.history:
            return dict.fromkeys(self.positions, 0.0)

        snapshot = next(reversed(self.history.values()))
        return snapshot.market_values.copy()

    @property
    def equity(self) -> float:
        """返回最近一次收盘时的账户总资产，首次收盘前为初始资金。"""
        if not self.history:
            return self.init_capital

        snapshot = next(reversed(self.history.values()))
        return snapshot.equity

    def record_daily_snapshot(self, trade_date: str) -> None:

        market_values = dict.fromkeys(self.positions, 0.0)
        for symbol, quantity in self.positions.items():
            if quantity:
                close = self.data_handler.get_valuation_close(symbol, trade_date)
                market_values[symbol] = quantity * close

        self.history[trade_date] = Snapshot(
            positions=self.positions.copy(),
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
        )

    def update_portfolio(self, event : FillEvent):

        if event.type != "FILL":
            return

        quantity = event.quantity if event.direction == "BUY" else -event.quantity
        self.positions[event.symbol] += quantity
        self.cash -= (quantity * event.fill_price + event.commission)
        self.total_commission += event.commission
