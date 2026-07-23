STRATEGY_TEMPLATES = [
    {
        "key": "ma_crossover",
        "name": "MA Crossover",
        "name_zh": "均线交叉",
        "difficulty": "beginner",
        "category": "trend",
        "description": "Buy when the fast moving average crosses above the slow moving average.",
        "default_params": {"fast_period": 10, "slow_period": 30, "timeframe": "1D"},
    },
    {
        "key": "rsi_reversal",
        "name": "RSI Reversal",
        "name_zh": "RSI 反转",
        "difficulty": "beginner",
        "category": "mean_reversion",
        "description": "Buy after RSI recovers from oversold levels and sell near overbought levels.",
        "default_params": {"period": 14, "oversold": 30, "overbought": 70, "timeframe": "1D"},
    },
    {
        "key": "dca",
        "name": "Dollar Cost Averaging",
        "name_zh": "定投",
        "difficulty": "beginner",
        "category": "passive",
        "description": "Invest a fixed simulated amount at a regular interval.",
        "default_params": {"amount": 100, "interval_days": 7},
    },
]
