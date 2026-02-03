"""
Federal Reserve Economic Data (FRED) data source connector.

Maps FRED series to the standard so the same ETL and DB schema can be used.
"""

from datetime import date, datetime 
from typing import Optional 
import pandas as pd 
from src.data.models import AssetClass
from src.data.sources.base import DataSource, DataSource_error

try:
    from fredapi import Fred 
    FRED_AVAILABLE = True
except ImportError:
    FRED_AVAILABLE = False

class FREDSource(DataSource):
    """
    Federal Reserve Economic Data (FRED) data source connector.
    Fetch FRED series as a single 'close' series; open/high/low set to close, volume=0

    Example usage:
        source = FredSource()
        df = source.fetch_prices("AAPL", date(2023, 1, 1), date(2023, 1, 31))
    """

    def __init__(self, api_key: Optional[str] = None):
        import os
        raw = api_key if api_key is not None else os.environ.get("FRED_API_KEY")
        self._api_key = (raw or "").strip()
        if not FRED_AVAILABLE:
            raise DataSource_error("fredapi library not installed. Run: pip install fredapi")
        if not self._api_key:
            raise DataSource_error("FRED API key required. Set FRED_API_KEY environment variable or pass directly.")
        self._fred = Fred(api_key=self._api_key)

    @property
    def source_name(self) -> str:
        return "FRED"

    def fetch_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        try:
            s = self._fred.get_series(symbol, start_date.isoformat(), end_date.isoformat())
        except Exception as e:
            raise DataSource_error(f"Error fetching prices for {symbol}: {str(e)}") from e
        if s is None or s.empty:
            raise DataSource_error(f"No data found for {symbol}")

        s = s.dropna()
        df = pd.DataFrame({
            "date": s.index.date,
            "open": s.values,
            "high": s.values,
            "low": s.values,
            "close": s.values,
            "volume": 0,
            "adj_close": s.values,
            "source": self.source_name,
            "symbol": symbol,
        })
        return self.validate_data(df)

    def fetch_instrument_info(self, symbol: str) -> dict:
        try:
            info = self._fred.get_series_info(symbol)
            title = getattr(info, "title", symbol)
        except Exception as e:
            title = symbol 
        return {
            "symbol": symbol,
            "name": title,
            "exchange": "FRED",
            "industry": "Unknown",
            "currency": "USD",
            "asset_class": AssetClass.EQUITY,
            "first_trade_date": None,
            "last_trade_date": None,
            "sector": "Unknown",
        }