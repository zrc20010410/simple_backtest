class OptionPortfolio(BasePortfolio):
    """权利金收付型期权账户，保证金由行情源按每张义务仓提供。

    get_value(symbol, date, field) 在增加义务仓时提供 open_margin_per_contract
    （开仓时已知）。日终估值使用当日 settle、multiplier 和 margin_per_contract。
    保证金按独立合约计提，不含组合抵扣或备兑证券。
    """

    def __init__(self, events, data_handler: DataHandler, start_date, init_capital):
        super().__init__(events, data_handler, start_date, init_capital)
        self.positions = {symbol: OptionPosition() for symbol in data_handler.symbol_list}
        self._margin_by_symbol = dict.fromkeys(self.positions, 0.0)

    @property
    def margin_used(self) -> float:
        return sum(self._margin_by_symbol.values())

    @property
    def available_cash(self) -> float:
        return self.cash - self.margin_used

    def _market_field(self, symbol, trade_date, field: str) -> float:
        raw = self.data_handler.get_value(symbol, trade_date, field)
        try:
            value = float(raw)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{symbol} 在 {trade_date} 的 {field} 无效：{raw!r}") from exc
        if not isfinite(value) or value < 0 or (field == "multiplier" and value == 0):
            raise ValueError(f"{symbol} 在 {trade_date} 的 {field} 无效：{raw!r}")
        return value

    def update_portfolio(self, event: FillEvent) -> None:
        if event.type != "FILL":
            return
        if not isinstance(event, OptionFillEvent):
            raise TypeError("OptionPortfolio 需要含开平标志和乘数的 OptionFillEvent")
        old = self.positions[event.symbol]
        new = old.after_fill(event)
        if not isfinite(event.fill_price) or event.fill_price < 0:
            raise ValueError("期权成交价格必须是有限非负数")

        margin = self._margin_by_symbol[event.symbol]
        if new.short_qty > old.short_qty:
            per_contract = self._market_field(event.symbol, event.datetime, "open_margin_per_contract")
            margin += event.quantity * per_contract
        elif new.short_qty < old.short_qty:
            margin = (margin / old.short_qty) * new.short_qty

        premium = event.quantity * event.fill_price * event.multiplier
        self._book_fill_cash(premium if event.direction == "BUY" else -premium, event.commission)
        self.positions[event.symbol] = new
        self._margin_by_symbol[event.symbol] = margin

    def record_daily_snapshot(self, trade_date: str) -> None:
        market_values = dict.fromkeys(self.positions, 0.0)
        margins = dict.fromkeys(self.positions, 0.0)
        for symbol, position in self.positions.items():
            if position.net_qty:
                price = self._market_field(symbol, trade_date, "settle")
                multiplier = self._market_field(symbol, trade_date, "multiplier")
                market_values[symbol] = position.net_qty * price * multiplier
            if position.short_qty:
                per_contract = self._market_field(symbol, trade_date, "margin_per_contract")
                margins[symbol] = position.short_qty * per_contract

        margin_used = sum(margins.values())
        snapshot = OptionSnapshot(
            positions={symbol: pos.net_qty for symbol, pos in self.positions.items()},
            market_values=market_values,
            cash=self.cash,
            total_commission=self.total_commission,
            equity=self.cash + sum(market_values.values()),
            option_positions=self.positions.copy(),
            margin_used=margin_used,
            available_cash=self.cash - margin_used,
        )
        self._margin_by_symbol = margins
        self.history[trade_date] = snapshot