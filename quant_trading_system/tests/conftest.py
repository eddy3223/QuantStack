import pytest 
import pandas as pd 
import numpy as np

from backtest.engine import VectorizedBacktestEngine
from signals.momentum import momentum_signal
from core.market_data import MarketData

@pytest.fixture
def market_data():
    dates = pd.date_range("2020-01-01", period=200)
    
    def make_price(seed):
        rng = np.random.default_rng(seed)
        returns = rng.normal(0, 0.01, size=len(dates))
        prices = 100* (1+returns).cumprod()
        return pd.DataFrame(
            {
                "open":prices,
                "high":prices *1.01,
                "low" :prices * 0.99,
                "close": prices,
                "volumne" : 1_000,
            },
            index=dates
        )
    return MarketData(
        {
            "SPY": make_price(1),
            "TLT": make_price(2)
        }
    )

@pytest.fixture 
def backtest_results(market_data):
    prices = pd.concat(
        {
            sym: df['close']
            for sym, df in market_data.items()
        },
        axis = 1
    )

    signals = momentum_signal(prices, window=20)

    engine = VectorizedBacktestEngine(
        market_data= market_data,
        instruments= None,
        vol_window= 10,
        target_gross_exposure=1.0
    )

    return engine.run(signals)