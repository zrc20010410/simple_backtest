from dataclasses import dataclass
from datahandler.options_data_handler import OptionsDataHandler
from event import FillEvent, OptionFillEvent
from portfolio.abs_portfolio import ABSPortfolio, Snapshot
from utils.mo_margin import mo_margin_per_contract


@dataclass
class OptionSnapshot(Snapshot):
    margin_used: float
    available_cash: float


class OptionPortfolio(ABSPortfolio):
    data_handler: OptionsDataHandler
    def __init__(self, events, data_handler: OptionsDataHandler, start_date, init_capital):
        super().__init__(events, data_handler, start_date, init_capital)
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

        if not isinstance(event, OptionFillEvent):
            raise TypeError("OptionPortfolio 需要 OptionFillEvent")

        symbol = event.symbol
        old = self.positions[symbol]
        quantity = event.quantity
        change = quantity if event.direction == "BUY" else -quantity
        new = old + change
        margin = self._margin_by_symbol[symbol]

        if event.signal_type not in ("OPEN", "CLOSE"):
            raise ValueError(f"未知的开平标志 {event.signal_type!r}")

        closed = min(abs(old), quantity) if old * change < 0 else 0
        opened = quantity - closed
        if event.signal_type == "CLOSE" and opened:
            raise ValueError(f"{symbol} 没有足够的相应持仓可平")

        # 持有空仓
        if old < 0 and closed:
            margin *= (abs(old) - closed) / abs(old)

        # 开空
        if change < 0 and opened:
            inputs = self.data_handler.get_margin_inputs(symbol, event.datetime, at_open=True)
            margin += opened * mo_margin_per_contract(**inputs)

        cost = round(change * event.fill_price * self.data_handler.contract_multiplier, 2)
        self.positions[symbol] = new
        self.cash -= (cost + event.commission)
        self.total_commission += event.commission
        self._margin_by_symbol[symbol] = margin

    def record_daily_snapshot(self, trade_date: str) -> None:

        self._settle_expired_positions(trade_date)

        market_values = dict.fromkeys(self.positions, 0.0)
        margins = dict.fromkeys(self.positions, 0.0)
        for symbol, quantity in self.positions.items():
            if quantity == 0:
                continue
            if quantity < 0:
                inputs = self.data_handler.get_margin_inputs(symbol, trade_date)
                margins[symbol] = -quantity * mo_margin_per_contract(**inputs)
                settle = inputs["settle"]
            else:
                settle = self.data_handler.get_value(symbol, trade_date, "settle")
            market_values[symbol] = quantity * settle * self.data_handler.contract_multiplier

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

    def _settle_expired_positions(self, trade_date: str, fee_per_contract: float = 2.0) -> None:
        settlements = []

        for symbol, quantity in self.positions.items():
            if quantity == 0:
                continue

            date = symbol.split("-", 1)[0]  # MO2303-P-6600 -> MO2303
            if self.data_handler.expiry_dates.get(date) != trade_date:
                continue

            settle = self.data_handler.get_value(symbol, trade_date, "settle")
            value_per_contract = round(settle * self.data_handler.contract_multiplier, 2)

            if value_per_contract > fee_per_contract:
                cash_flow = quantity * value_per_contract
                fee = abs(quantity) * fee_per_contract
            else:
                cash_flow = 0.0
                fee = 0.0

            settlements.append((symbol, cash_flow, fee))

        for symbol, cash_flow, fee in settlements:
            self.cash += cash_flow - fee
            self.total_commission += fee
            self.positions[symbol] = 0
            self._margin_by_symbol[symbol] = 0.0
