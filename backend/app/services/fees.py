from dataclasses import dataclass

from app.schemas.simulation import FeeLineRead, FeeScheduleRead, SimulationFeeSchedulesRead


@dataclass(frozen=True)
class FeeBreakdown:
    tax: float
    commission: float
    platform_fee: float
    settlement_fee: float
    regulatory_fee: float

    @property
    def total(self) -> float:
        return self.tax + self.commission + self.platform_fee + self.settlement_fee + self.regulatory_fee


class FutuFeeService:
    HK_SOURCE = "https://www.futuhk.com/support/topic2_335"
    US_SOURCE = "https://www.futuhk.com/support/topic2_283"

    @staticmethod
    def schedule() -> SimulationFeeSchedulesRead:
        return SimulationFeeSchedulesRead(
            schedules=[
                FeeScheduleRead(
                    market="HK",
                    title="港股模拟费率",
                    lines=[
                        FeeLineRead(name="佣金", value="成交金额 * 0.03%，最低 3 HKD"),
                        FeeLineRead(name="平台使用费", value="15 HKD / 笔"),
                        FeeLineRead(name="印花税", value="股票卖出按成交金额 * 0.1% 近似计算"),
                        FeeLineRead(name="交收费", value="成交金额 * 0.0042%"),
                        FeeLineRead(name="交易费及征费", value="成交金额 * (0.00565% + 0.0027% + 0.00015%)"),
                    ],
                    settlement_note="港股模拟按 T+2 处理：新买入数量在交收日前不可卖出。",
                    source_url=FutuFeeService.HK_SOURCE,
                ),
                FeeScheduleRead(
                    market="US",
                    title="美股模拟费率",
                    lines=[
                        FeeLineRead(name="佣金", value="0.0049 USD / 股，最低 0.99 USD"),
                        FeeLineRead(name="平台使用费", value="0.005 USD / 股，最低 1 USD"),
                        FeeLineRead(name="交收费", value="0.003 USD / 股"),
                        FeeLineRead(name="SEC 规费", value="仅卖出，成交金额 * 0.0000206，最低 0.01 USD"),
                        FeeLineRead(name="交易活动费", value="仅卖出，0.000195 USD / 股，最低 0.01 USD，最高 9.79 USD"),
                    ],
                    settlement_note="美股模拟按 T+1 处理：新买入数量在交收日前不可卖出。",
                    source_url=FutuFeeService.US_SOURCE,
                ),
            ]
        )

    @staticmethod
    def calculate(exchange: str, side: str, gross_amount: float, quantity: float) -> FeeBreakdown:
        normalized_exchange = exchange.upper()
        normalized_side = side.lower()
        if normalized_exchange == "HK":
            commission = max(gross_amount * 0.0003, 3)
            platform_fee = 15
            settlement_fee = gross_amount * 0.000042
            tax = gross_amount * 0.001 if normalized_side == "sell" else 0
            regulatory_fee = gross_amount * (0.0000565 + 0.000027 + 0.0000015)
            return FeeBreakdown(
                tax=tax,
                commission=commission,
                platform_fee=platform_fee,
                settlement_fee=settlement_fee,
                regulatory_fee=regulatory_fee,
            )

        if normalized_exchange == "US":
            commission = max(quantity * 0.0049, 0.99)
            platform_fee = max(quantity * 0.005, 1)
            settlement_fee = quantity * 0.003
            regulatory_fee = 0
            if normalized_side == "sell":
                regulatory_fee = max(gross_amount * 0.0000206, 0.01) + min(max(quantity * 0.000195, 0.01), 9.79)
            return FeeBreakdown(
                tax=0,
                commission=commission,
                platform_fee=platform_fee,
                settlement_fee=settlement_fee,
                regulatory_fee=regulatory_fee,
            )

        commission = gross_amount * 0.0003
        return FeeBreakdown(tax=0, commission=commission, platform_fee=0, settlement_fee=0, regulatory_fee=0)
