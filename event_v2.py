from math import isfinite

from event import FillEvent


class OptionFillEvent(FillEvent):
    """quantity 为张数乘以成交日合约乘数，fill_price 为每单位权利金。"""

    def __init__(self, datetime, symbol, exchange, quantity, direction, fill_price, *, signal_type: str,
                 commission: float):
        if direction not in ("BUY", "SELL"):
            raise ValueError("direction 必须是 BUY 或 SELL")
        if signal_type not in ("OPEN", "CLOSE"):
            raise ValueError("signal_type 必须是 OPEN 或 CLOSE")
        if isinstance(quantity, bool) or not isfinite(quantity) or quantity <= 0:
            raise ValueError("期权成交数量必须是有限正数")
        if commission is None or not isfinite(commission):
            raise ValueError("期权成交必须明确提供有效的手续费")

        super().__init__(
            datetime, symbol, exchange, quantity, direction, fill_price,
            commission=commission,
        )
        self.signal_type = signal_type
