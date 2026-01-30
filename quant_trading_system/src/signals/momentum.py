import pandas as pd 
import numpy as np 

def momentum_signal(
    prices: pd.DataFrame,
    window: int = 60,
) -> pd.DataFrame:
    """
    Simple time-series momentum: +1 if price > rolling mean else -1
    """
    rolling_mean = prices.rolling(window=window).mean()
    signals = (prices > rolling_mean).astype(int) * 2 - 1
    return signals