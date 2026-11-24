import matplotlib.pyplot as plt
from math import isclose, sqrt
from typing import Mapping
from portfolio.portfolio import Snapshot
import pandas as pd

from datahandler.data_handler import DEFAULT_INDEX_FILE

class PerformanceReport:

    def __init__(self, history: Mapping[str, Snapshot], initial_capital: float, trading_days_per_year: int = 252):

        self.initial_capital = initial_capital
        self.trading_days_per_year = trading_days_per_year

        equity = pd.Series({day: snap.equity for day, snap in history.items()}, dtype=float)
        equity.index = pd.to_datetime(equity.index, format="%Y%m%d")
        equity = equity.sort_index().rename_axis("trade_date")

        pre_equity = equity.shift(1)
        pre_equity.iloc[0] = initial_capital
        net_value = equity / initial_capital
        self.daily_snapshot = pd.DataFrame({
            "equity": equity,
            "daily_return": equity / pre_equity.where(pre_equity > 0) - 1,
            "net_value": net_value,
            "cumulative_return": net_value - 1,
            "drawdown": self._drawdown(net_value),
        })

    @staticmethod
    def _drawdown(net_value: pd.Series) -> pd.Series:
        peak = net_value.cummax().clip(lower=1.0)
        return net_value / peak - 1

    def summary(self) -> pd.Series:

        returns = self.daily_snapshot["daily_return"]
        trading_days_per_year = self.trading_days_per_year
        last_net_value = self.daily_snapshot["net_value"].iloc[-1]
        annual_return = volatility = sharpe = float("nan")
        if last_net_value >= 0 and returns.notna().all():
            annual_return = last_net_value ** (trading_days_per_year / len(returns)) - 1
        if len(returns) >= 2 and returns.notna().all():
            volatility = returns.std(ddof=1) * sqrt(trading_days_per_year)
            if not isclose(volatility, 0.0, abs_tol=1e-12):
                sharpe = returns.mean() * trading_days_per_year / volatility

        return pd.Series({
            "期初资金": self.initial_capital,
            "期末总资产": self.daily_snapshot["equity"].iloc[-1],
            "累计收益率": self.daily_snapshot["cumulative_return"].iloc[-1],
            "年化收益率": annual_return,
            "年化波动率": volatility,
            "最大回撤": abs(self.daily_snapshot["drawdown"].min()),
            "夏普比率": sharpe,
        })

    def print_summary(self) -> None:
        start, end = self.daily_snapshot.index[0], self.daily_snapshot.index[-1]
        print(f"{start:%Y-%m-%d} 至 {end:%Y-%m-%d}（{len(self.daily_snapshot)} 个交易日）")
        for name, value in self.summary().items():
            if pd.isna(value):
                display = "—"
            elif name in ("期初资金", "期末总资产"):
                display = f"{value:,.2f} 元"
            elif name == "夏普比率":
                display = f"{value:.2f}"
            else:
                display = f"{value:.2%}"
            print(f"{name}  {display}")

    def _benchmark_net_value(self, benchmark: str) -> pd.Series:
        indexes = pd.read_csv(DEFAULT_INDEX_FILE, usecols=["ts_code", "trade_date", "close", "pre_close"],
                              dtype={"ts_code": str, "trade_date": str})
        dates = self.daily_snapshot.index.strftime("%Y%m%d")
        selected = indexes.loc[(indexes["ts_code"] == benchmark) & indexes["trade_date"].isin(dates)]
        aligned = selected.set_index("trade_date").reindex(dates)
        pre_close = aligned["pre_close"].iloc[0]
        close = aligned["close"]
        net_value = close.where(close.gt(0) & close.lt(float("inf"))) / pre_close
        net_value.index = self.daily_snapshot.index
        return net_value

    def get_output(self, benchmark: str | None = None) -> pd.DataFrame:

        strategy_net_value = self.daily_snapshot["net_value"]
        strategy_drawdown = self.daily_snapshot["drawdown"]

        outputs = pd.DataFrame({'strategy_net_value': strategy_net_value, 'strategy_drawdown': strategy_drawdown,})
        if benchmark is not None:
            bench_net_value = self._benchmark_net_value(benchmark)
            bench_drawdown = self._drawdown(bench_net_value)
            outputs["bench_net_value"] = bench_net_value
            outputs["bench_drawdown"] = bench_drawdown

        return outputs

    def plot(self, benchmark: str | None = None, show: bool = True):

        dates = self.daily_snapshot.index.to_pydatetime()
        benchmark_nav = self._benchmark_net_value(benchmark) if benchmark is not None else None
        fig, (nav_ax, dd_ax) = plt.subplots(2, 1, sharex=True, figsize=(9, 5), gridspec_kw={"height_ratios": [2, 1]},
                                            constrained_layout=True)

        nav_ax.plot(dates, self.daily_snapshot["net_value"], color="red", label="Strategy NAV")
        if benchmark_nav is not None:
            nav_ax.plot(dates, benchmark_nav, color="#B39B41", linestyle="-", label=f"Benchmark NAV ({benchmark})")

        drawdown = self.daily_snapshot["drawdown"].to_numpy()
        dd_ax.plot(dates, drawdown, color="#1f77b4", label="Strategy Drawdown")
        if benchmark_nav is not None:
            dd_ax.plot(dates, self._drawdown(benchmark_nav), color="black", label=f"Benchmark Drawdown ({benchmark})")

        for axis, title in ((nav_ax, "Net Asset Value Curve"), (dd_ax, "Drawdown")):
            axis.set_title(title)
            axis.legend(loc="upper right", frameon=True, facecolor="white", edgecolor="0.65")
            axis.set_facecolor("#f4f7fa")
            axis.grid(True, axis="both", which="major", color="#cbd5df", linewidth=0.65)
        if show:
            plt.show()
        return fig
