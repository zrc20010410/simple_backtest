"""现金账户的持仓、逐日估值与成交记账。"""
from dataclasses import dataclass
from data_handler import DataHandler


@dataclass
class Snapshot:
    """单个交易日的账户快照。"""
    positions: dict[str, float]
    market_values: dict[str, float]
    cash: float
    total_commission: float
    equity: float


class Portfolio:

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):

        self.data_handler = data_handler
        self.events = events
        self.start_date = start_date
        self.init_capital = init_capital
        self.positions = dict.fromkeys(data_handler.symbol_list, 0)
        self.cash = init_capital
        self.total_commission = 0.0
        self.history = {}

    @property
    def market_values(self):
        """各标的市值 = 持仓数量 × 最新估值价格。"""
        values = {}
        for symbol, quantity in self.positions.items():
            if quantity == 0:
                values[symbol] = 0.0
                continue

            close = self.data_handler.get_value(symbol, self.events.datetime, "close")
            values[symbol] = quantity * close

        return values

    @property
    def equity(self):
        """账户总资产（现金加持仓市值）。"""
        return self.cash + sum(self.market_values.values())

    def _record(self, datetime):
        market_values = self.market_values
        self.history[datetime] = Snapshot(
            positions=self.positions.copy(),
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
        )

    def update_fill(self, event):
        """按成交单价结算，手续费只扣一次；同日成交会更新当天快照。"""
        if event.type != "FILL":
            return

        quantity = event.quantity if event.direction == "BUY" else -event.quantity
        self.positions[event.symbol] += quantity
        self.cash -= (quantity * event.fill_price + event.commission)
        self.total_commission += event.commission
        self._record(event.datetime)
