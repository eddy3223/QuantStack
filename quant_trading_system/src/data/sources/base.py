"""
Base class for all data source connectors.

This defines the interface that all data sources must implement.
Using an abstract base class ensures consistency across different
data vendors (e.g. Yahoo Finance, Alpha Vantage, etc.).
"""

from abc import ABC, abstractmethod
from datetime import date 
from typing import Optional 
import pandas as pd

from pydantic import BaseModel

class PriceData(BaseModel):
    """
    Standardized price data structure.

    All data sources must convert their data to this format.
    This ensures consistency across all data sources and makes it easy to load into the database.
    """
    symbol: str
    date: date
    open: Optional[float] = None
    high: Optional[float] = None
    low: Optional[float] = None
    close: Optional[float] = None
    volume: Optional[int] = None
    adj_close: Optional[float] = None
    source: str

    class Config:
        # Allow creating from ORM objects 
        from_attributes = True

class DataSource(ABC):
    """
    Abstract base class for data source connectors.

    All data sources (eg. Yahoo Finance, Alpha Vantage, etc.) must inherit from this class
    and implement the abstract methods.

    This pattern is called the "Template Method Pattern" it defines the skeleton 
    of an algorithm and lets subclasses fill in the details.
    """

    @property 
    @abstractmethod
    def source_name(self) -> str:
        """Return the name of this data source."""
        pass

    @abstractmethod
    def fetch_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Fetch price data for a given symbol and date range.

        Args:
            symbol: The Ticker to fetch data for.
            start_date: Start of date range
            end_date: End of date range

        Returns:
            DataFrame with columns: date, open, high, low, close, volume, adj_close

        Raises:
            DataSourceError: If the data cannot be fetched.
        """ 
        pass 

    @abstractmethod
    def fetch_instrument_info(self, symbol: str) -> dict:
        """
        Fetch metadata about an instrument.

        Args:
            symbol: The Ticker symbol 
        
        Returns:
            Dict with keys: name, exchange, sector, industry, etc.
        """

    def validate_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate and clean the data returned by the data source.

        This is a shared method - all sources use same validation logic.
        """

        if df.empty:
            return df 

        #ensure required columns exist
        required_cols = ["date", "open", "high", "low", "close", "volume"]
        for col in required_cols:
            if col not in df.columns:
                raise DataSource_error(f"Missing required column: {col}")

        #remove nulls
        price_cols = ["open", "high", "low", "close"]
        df = df.dropna(subset=price_cols, how = 'all')

        df = df.sort_values(by="date").reset_index(drop=True)

        return df 

class DataSource_error(Exception):
    """Raised when a data source operation fails."""
    pass