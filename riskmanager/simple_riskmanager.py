"""固定买入 100 股，按实际持仓平仓的只做多风控。"""

from .abs_riskmanager import RiskManager

class SimpleRiskManager(RiskManager):
    def __init__(self):
        pass

    def risk_manager(self, signal):
        pass
