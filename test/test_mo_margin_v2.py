import unittest

from event_v2 import OptionFillEvent
from mo_margin_v2 import mo_margin_per_contract, mo_margin_rates
from portfolio_v2 import OptionPortfolio


class MOMarginTests(unittest.TestCase):
    def test_call_and_put_ordinary_and_floor_branches(self):
        # 指数 6000，调整系数 15%，结算价 10 点。深度虚值认沽底线按行权价 4000 算。
        cases = [
            ("MO2603-C-6200", 71_000),
            ("MO2603-C-7200", 46_000),
            ("MO2603-P-5800", 71_000),
            ("MO2603-P-4000", 31_000),
        ]
        for symbol, expected in cases:
            with self.subTest(symbol=symbol):
                self.assertAlmostEqual(mo_margin_per_contract(symbol, 10, 6000, 0.15, 0.5), expected)

    def test_index_close_rounded_half_up_before_calculation(self):
        # 6000.125 按细则化为 6000.13；实值看涨虚值额为零。
        amount = mo_margin_per_contract("MO2603-C-5000", 10, 6000.125, 0.15, 0.5)
        self.assertAlmostEqual(amount, 91_001.95)

    def test_rates_apply_from_effective_date(self):
        schedule = {"20260107": (0.18, 0.6), "20260105": (0.15, 0.5)}
        with self.assertRaises(ValueError):
            mo_margin_rates("20260104", schedule)
        self.assertEqual(mo_margin_rates("20260105", schedule), (0.15, 0.5))
        self.assertEqual(mo_margin_rates("20260106", schedule), (0.15, 0.5))
        self.assertEqual(mo_margin_rates("20260107", schedule), (0.18, 0.6))

    def test_intraday_collateral_and_two_daily_snapshots(self):
        symbol = "MO2603-C-6200"

        class Quotes:
            symbol_list = [symbol]

            def __init__(self):
                # 前收盘 5950、前结算价 9，开仓时只能取得上一日的每手占用。
                self.fields = {"20260105": {"open_margin_per_contract": 65_150, "multiplier": 100}}

            def get_value(self, contract, day, field):
                if contract != symbol:
                    raise KeyError(contract)
                return self.fields[day][field]

        quotes = Quotes()
        account = OptionPortfolio(None, quotes, "20260105", 1_000_000)
        fill = OptionFillEvent("20260105", symbol, "CFFEX", 200, "SELL", 12,
                               signal_type="OPEN", commission=5)
        account.update_portfolio(fill)
        self.assertEqual(account.positions[symbol], -2)
        self.assertEqual(account.margin_used, 130_300)

        quotes.fields["20260105"].update(settle=10, underlying_close=6000,
                                         margin_adjustment=0.15, minimum_protection=0.5)
        account.record_daily_snapshot("20260105")
        first = account.history["20260105"]
        self.assertEqual(first.cash, 1_002_395)
        self.assertEqual(first.margin_used, 142_000)
        self.assertEqual(first.available_cash, 860_395)
        self.assertEqual(first.equity, 1_000_395)

        # 无成交也按新结算价及指数收盘价重算，保证金只改变可用资金。
        quotes.fields["20260106"] = dict(settle=20, underlying_close=6100, multiplier=100,
                                         margin_adjustment=0.15, minimum_protection=0.5)
        account.record_daily_snapshot("20260106")
        second = account.history["20260106"]
        self.assertEqual(second.positions, {symbol: -2})
        self.assertEqual(second.cash, first.cash)
        self.assertEqual(second.margin_used, 167_000)
        self.assertEqual(second.available_cash, 835_395)
        self.assertEqual(second.equity, 998_395)
        self.assertEqual(first.margin_used, 142_000)


if __name__ == "__main__":
    unittest.main()
