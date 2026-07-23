class FxService:
    DEFAULT_USD_HKD = 7.8

    def usd_hkd(self) -> float:
        return self.DEFAULT_USD_HKD

    def to_hkd(self, amount: float, currency: str) -> float:
        normalized = currency.upper()
        if normalized == "HKD":
            return amount
        if normalized == "USD":
            return amount * self.usd_hkd()
        return amount

    def from_hkd(self, amount_hkd: float, currency: str) -> float:
        normalized = currency.upper()
        if normalized == "HKD":
            return amount_hkd
        if normalized == "USD":
            return amount_hkd / self.usd_hkd()
        return amount_hkd

