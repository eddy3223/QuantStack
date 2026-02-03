"""
Stub / mock data source for resting and demos.

Implements the DataSource interface with synthetic data.
Useful for testing and demonstrating multi-vendor abstraction 
without external API keys.
"""

from datetime import date, timedelta 
import pandas as pd 
import numpy as np 

from src.data.sources.base import DataSource, DataSource_error
from src.data.models import AssetClass

class StubSource(DataSource):
    """Returns synthetic data for any symbol and date range."""

    @property
    def source_name(self) -> str:
        return "Stub"

    def fetch_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Fetch synthetic prices for a given symbol and date range.

        Args:
            symbol: The symbol to fetch data for.
            start_date: Start of date range.
            end_date: End of date range.

        Returns:
            DataFrame with columns: date, open, high, low, close, volume.
        """

        dates = pd.date_range(start_date, end_date, freq= "B")
        n = len(dates)
        if n== 0:
            raise DataSource_error(f"No business days in range {start_date} to {end_date}")

        np.random.seed(hash(symbol)% 2**32)
        close = 100 * (1 + np.cumsum(np.random.randn(n) * 0.01))
        close = np.maximum(close, 1.0)
        df = pd.DataFrame({
            "date": [d.date() for d in dates],
            "open": close,
            "high": close * (1 + np.random.randn(n) * 0.01),
            "low": close * (1 - np.random.randn(n) * 0.01),
            "close": close,
            "volume": np.random.randint(1000000, 5000000, n),
            "adj_close": close,
            "source": self.source_name,
            "symbol": symbol,
        })
        df = df.sort_values(by="date").reset_index(drop=True)
        return self.validate_data(df)

    def fetch_instrument_info(self, symbol: str) -> dict:
        return {
            "symbol": symbol,
            "name": symbol,
            "exchange": "Stub",
            "industry": "Unknown",
            "currency": "USD",
            "asset_class": AssetClass.EQUITY,
            "first_trade_date": None,
            "last_trade_date": None,
        }
