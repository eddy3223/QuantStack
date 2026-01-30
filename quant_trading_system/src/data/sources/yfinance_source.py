"""
Yahoo Finance data source connector.

This implements the DataSourceBase interface for Yahoo Finance.
Yahoo Finance is free and good for learning/prototyping but production systems
should use Bloomberg, Refinitive or similar
"""

from datetime import date, datetime 
from typing import Optional 
import pandas as pd 
import yfinance as yf 

from src.data.sources.base import DataSource, DataSource_error
from src.data.models import AssetClass

class YFinanceSource(DataSource):
    """
    Yahoo Finance data source connector.

    Example usage:
        source = YFinanceSource()
        df = source.fetch_prices("AAPL", date(2023, 1, 1), date(2023, 1, 31))
    """

    @property
    def source_name(self) -> str:
        return "Yahoo Finance"

    def fetch_prices(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
    ) -> pd.DataFrame:
        """
        Fetch historical prices from Yahoo Finance.

        Args:   
            symbol: The Ticker symbol
            start_date: Start of date range
            end_date: End of date range

        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            ticker = yf.Ticker(symbol)

            df = ticker.history(
                start = start_date.isoformat(),
                end = (datetime.combine(end_date, datetime.min.time()) + pd.Timedelta(days=1)).strftime('%Y-%m-%d'),
                auto_adjust = False # Keep both close and Adj close
            )

            if df.empty:
                raise DataSource_error(f"No data found for {symbol}")

            df = df.reset_index()
            df.columns = df.columns.str.lower().str.replace(' ', '_')

            #Rename columns to match our standard
            column_mapping = {
                'date': 'date',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume',
                'adjclose': 'adj_close',
            }

            # Keep only columns we need 
            df = df[[col for col in column_mapping.keys() if col in df.columns]]
            df = df.rename(columns=column_mapping)

            #convert date to data type 
            df['date'] = pd.to_datetime(df['date']).dt.date

            # Add source identifier 
            df['source'] = self.source_name
            df['symbol'] = symbol

            # validate using base class method
            df = self.validate_data(df)

            return df 

        except Exception as e:
            raise DataSource_error(f"Error fetching prices for {symbol}: {str(e)}") from e

    def fetch_instrument_info(self, symbol: str) -> dict:
        """
        Fetch metadata about an instrument from Yahoo Finance.

        Returns dict with: name, exchange, sector, industry, etc.
        """
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            # map yfinance keys to our standard
            return {
                'symbol': symbol,
                'name': info.get('longName') or info.get('shortName', symbol),
                'exchange': info.get('exchange', 'Unknown'),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'currency': info.get('currency', 'USD'),
                'asset_class': self._infer_asset_class(info),
                'first_trade_date': info.get('firstTradeDate', None),
                'last_trade_date': info.get('lastTradeDate', None),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
            }

        except Exception as e:
            raise DataSource_error(f"Error fetching instrument info for {symbol}: {str(e)}") from e 

    def _infer_asset_class(self, info: dict) -> str:
        """Infer asset class from yfinance info."""
        quote_type = info.get('quoteType', '').upper()

        mapping = {
            'EQUITY': AssetClass.EQUITY,
            'ETF': AssetClass.ETF,
            'FUTURE': AssetClass.FUTURE,
            'OPTION': AssetClass.OPTION,
            'FOREX': AssetClass.FOREX,
            'CRYPTOCURRENCY': AssetClass.CRYPTO,
            'INDEX': AssetClass.EQUITY,
            'MUTUALFUND': AssetClass.ETF,
            'BOND': AssetClass.EQUITY,
            'COMMODITY': AssetClass.EQUITY,
            'OTHER': AssetClass.EQUITY,
        }

        return mapping.get(quote_type, AssetClass.EQUITY)
         

    def fetch_multiple(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        """
        Fetch prices for multiple symbols and date range.

        Returns:
            Dict of symbol -> DataFrame with columns: date, open, high, low, close, volume
            Failed symbols are skipped with a warning
        """

        results = {}

        for symbol in symbols:
            try:
                df = self.fetch_prices(symbol, start_date, end_date)
                results[symbol] = df
                print(f"  ✓ {symbol}: {len(df)} rows")
            except DataSource_error as e:
                print(f"  ✗ {symbol}: {e}")

        return results