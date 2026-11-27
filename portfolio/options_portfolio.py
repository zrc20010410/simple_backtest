from dataclasses import dataclass

from config import EXPIRED_FEE_PER_CONTRACT
from datahandler.options_data_handler import OptionsDataHandler
from event import FillEvent, OptionFillEvent
from portfolio.abstract_portfolio import AbstractPortfolio, Snapshot
from utils.mo_margin import mo_margin_per_contract


@dataclass
class OptionSnapshot(Snapshot):
    margin_used: float
    available_cash: float

@dataclass(frozen=True)
class OpeningRisk:
    cash: float
    margin_used: float

    @property
    def available_cash(self) -> float:
        return round(self.cash - self.margin_used, 2)

class OptionsPortfolio(AbstractPortfolio):
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

        if not isinstance(event, OptionFillEvent):
            raise TypeError("OptionPortfolio 需要 OptionFillEvent")

        symbol = event.symbol
        quantity = event.quantity
        old = self.positions[symbol]
        change = quantity if event.direction == "BUY" else -quantity
        new = old + change
        margin = self._margin_by_symbol[symbol]

        if event.signal_type == "CLOSE" and old < 0:
            margin *= abs(new) / abs(old)
        elif event.signal_type == "OPEN" and change < 0:
            inputs = self.data_handler.get_margin_inputs(symbol, event.datetime, at_open=True)
            margin += event.quantity * mo_margin_per_contract(**inputs)

        cost = round(change * event.fill_price * self.data_handler.contract_multiplier, 2)
        self.positions[symbol] = new
        self.cash -= (cost + event.commission)
        self.total_commission += event.commission
        self._margin_by_symbol[symbol] = margin

    def record_daily_snapshot(self, trade_date: str) -> None:
        self._settle_expired_positions(trade_date)
        snapshot, margins = self._build_snapshot(trade_date, at_open=False)
        self.history[trade_date] = snapshot
        self._margin_by_symbol = margins

    def get_position_margin(self, symbol: str) -> float:
        """返回该合约当前实际占用的保证金，单位为元。"""
        return self._margin_by_symbol[symbol]

    def _build_snapshot(self, trade_date: str, *, at_open: bool,) -> tuple[OptionSnapshot, dict[str, float]]:
        """构建开盘或盘后的快照"""
        market_values = dict.fromkeys(self.positions, 0.0)
        margins = dict.fromkeys(self.positions, 0.0)
        for symbol, quantity in self.positions.items():
            if quantity == 0:
                continue
            if quantity < 0 :
                inputs = self.data_handler.get_margin_inputs(symbol, trade_date, at_open = at_open)
                margins[symbol] = -quantity * mo_margin_per_contract(**inputs)
                price = (self.data_handler.get_value(symbol, trade_date, "open")
                         if at_open else inputs["settle"])
            else:
                field = "open" if at_open else "settle"
                price = self.data_handler.get_value(symbol, trade_date, field)
            market_values[symbol] = quantity * price * self.data_handler.contract_multiplier

        margin_used = sum(margins.values())
        snapshot = OptionSnapshot(
            positions=self.positions.copy(),
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
            margin_used=margin_used,
            available_cash=self.cash - margin_used,
        )
        return snapshot, margins

    def _settle_expired_positions(self, trade_date: str, fee_per_contract: float = EXPIRED_FEE_PER_CONTRACT) -> None:
        """收盘清算"""
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

    def record_daily_snapshot2(self, trade_date: str) -> None:

        self._settle_expired_positions(trade_date)

        market_values = dict.fromkeys(self.positions, 0.0)
        margins = dict.fromkeys(self.positions, 0.0)
        for symbol, quantity in self.positions.items():
            if quantity == 0:
                continue
            if quantity < 0:
                inputs = self.data_handler.get_margin_inputs(symbol, trade_date, at_open=False)
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