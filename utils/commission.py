
class Commission:
    def __init__(self):
        pass

    @staticmethod
    def stock_commission(fill_price: float, quantity: int, direction: str):
        """
            手续费: 0.01%
            印花税: 0.05%
        """
        min_commission = 5
        commission_rate = 0.0001
        stamp_tax_rate = 0.0005

        commission = max(min_commission, commission_rate * (fill_price * quantity))
        stamp_tax = stamp_tax_rate * (fill_price * quantity) if direction == 'SELL' else 0
        total_cost = commission + stamp_tax

        return total_cost