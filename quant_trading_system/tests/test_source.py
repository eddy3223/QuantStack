"""Test the Yahoo Finance data source connector."""

import sys 
sys.path.insert(0, ".")

from datetime import date
from src.data.sources.yfinance_source import YFinanceSource

source = YFinanceSource()

print("=" * 60)
print("Testing Yahoo Finance Data Source")
print("=" * 60)

# Fetch instrument info
print("\nFetching instrument info...")
info = source.fetch_instrument_info("AAPL")
for key, value in info.items():
    print(f"  {key}: {value}")

# Fetch prices
print("\nFetching prices...")
end = date.today()
start = date(end.year -1 if end.month == 1 else end.year, end.month - 2 if end.month > 1 else 12, end.day)

df = source.fetch_prices("AAPL", start, end)
print(f"    Rows: {len(df)}")
print(f"    Columns: {df.columns.tolist()}")
print(f"    Date range: {start} to {end}")
print("\n    Sample:")
print(df.head().to_string(index=False))

# Fetch multiple symbols
print("\nFetching multiple symbols...")
symbols = ["AAPL", "GOOG", "MSFT", "AMZN", "TSLA", 'INVALID_SYMBOL']
results = source.fetch_multiple(symbols, start, end)

print(f"\n    Successfully fetched {list(results.keys())}")

print("\n" + "=" * 60)
print("Done!")
print("=" * 60)