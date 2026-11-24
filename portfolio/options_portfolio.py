from dataclasses import dataclass
from math import isfinite
from numbers import Integral
from datahandler.data_handler import DataHandler
from event import FillEvent, OptionFillEvent
from portfolio.portfolio import Snapshot
from portfolio.abs_portfolio import ABSPortfolio

@dataclass
class OptionSnapshot(Snapshot):
    margin_used: float
    available_cash: float

class OptionPortfolio(ABSPortfolio):

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):
        super().__init__(events, data_handler, start_date, init_capital)
        self.positions = dict.fromkeys(data_handler.symbol_list, 0)
        self._margin_by_symbol = dict.fromkeys(self.positions, 0.0)

    @property
    def total_margin(self) -> float:
        return sum(self._margin_by_symbol.values())

    @property
    def available_cash(self) -> float:
        return self.cash - self.total_margin

    def update_portfolio(self, event: FillEvent) -> None:
        if event.type != "FILL":
            return

        old_quantity = self.positions[event.symbol]
        change = event.quantity if event.direction == "BUY" else -event.quantity
        new_quantity = old_quantity + change
        margin = self._margin_by_symbol[event.symbol]
        if new_quantity < 0 and new_quantity < old_quantity:
            # TODO
            per_contract = self.data_handler.get_value(event.symbol, event.datetime, "open_margin_per_contract")
            margin += event.quantity * per_contract
        elif old_quantity < 0 and new_quantity > old_quantity:
            margin *= abs(new_quantity) / abs(old_quantity)

        self.positions[event.symbol] = new_quantity
        self.cash -= (change * event.fill_price + event.commission)
        self.total_commission += event.commission
        self._margin_by_symbol[event.symbol] = margin

    def record_daily_snapshot(self, trade_date: str) -> None:
        # TODO
        market_values = dict.fromkeys(self.positions, 0.0)
        margins = dict.fromkeys(self.positions, 0.0)
        for symbol, position in self.positions.items():
            if position:
                price = self._market_field(symbol, trade_date, "settle")
                multiplier = self._market_field(symbol, trade_date, "multiplier")
                market_values[symbol] = position * price * multiplier
            if position < 0:
                if symbol.upper().startswith("MO"):
                    per_contract = mo_margin_for_day(self.data_handler, symbol, trade_date)
                else:
                    per_contract = self._market_field(symbol, trade_date, "margin_per_contract")
                margins[symbol] = abs(position) * per_contract

        margin_used = sum(margins.values())
        self.history[trade_date] = OptionSnapshot(
            positions=self.positions.copy(),
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
            margin_used=margin_used,
            available_cash=self.cash - margin_used,
        )
        self._margin_by_symbol = margins