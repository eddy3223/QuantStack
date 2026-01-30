import pandas as pd 
from typing import Dict 

class MarketData:
    def __init__(self, data: Dict[str, pd.DataFrame]):
        """
        data: dict of symbol -> SPY dataframe
        """
        self.data = data

    def get_close(self)
        """
        Return closeing prices for all symbols
        """
        return pd.concat({sym: df["close"] for sym, df in self.data.items()}, axis=1)

    def symbols(self):
        return list(self.data.keys())