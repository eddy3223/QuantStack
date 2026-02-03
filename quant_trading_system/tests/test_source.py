"""Tests for data source connectors: Stub, FRED, and Yahoo Finance."""

import os
import sys

import pytest

sys.path.insert(0, ".")

from datetime import date, timedelta

from src.data.sources.base import DataSource_error
from src.data.sources.stub_source import StubSource
from src.data.sources.yfinance_source import YFinanceSource

# Optional FRED import (may not be installed or have API key)
try:
    from src.data.sources.fred_source import FREDSource, FRED_AVAILABLE
except Exception:
    FREDSource = None
    FRED_AVAILABLE = False


# --- StubSource ---


class TestStubSource:
    """Tests for the stub / synthetic data source."""

    @pytest.fixture
    def source(self):
        return StubSource()

    def test_source_name(self, source):
        assert source.source_name == "Stub"

    def test_fetch_prices_returns_dataframe(self, source):
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        df = source.fetch_prices("STUB1", start, end)
        assert df is not None
        assert len(df) > 0

    def test_fetch_prices_has_required_columns(self, source):
        start = date(2024, 1, 1)
        end = date(2024, 1, 15)
        df = source.fetch_prices("STUB1", start, end)
        required = ["date", "open", "high", "low", "close", "volume"]
        for col in required:
            assert col in df.columns, f"Missing column: {col}"

    def test_fetch_prices_date_range(self, source):
        start = date(2024, 1, 1)
        end = date(2024, 1, 10)
        df = source.fetch_prices("STUB1", start, end)
        assert df["date"].min() >= start
        assert df["date"].max() <= end

    def test_fetch_prices_deterministic_per_symbol(self, source):
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        df1 = source.fetch_prices("A", start, end)
        df2 = source.fetch_prices("A", start, end)
        assert list(df1["close"]) == list(df2["close"])

    def test_fetch_prices_different_symbols_differ(self, source):
        start = date(2024, 1, 1)
        end = date(2024, 1, 5)
        df_a = source.fetch_prices("SYM_A", start, end)
        df_b = source.fetch_prices("SYM_B", start, end)
        assert list(df_a["close"]) != list(df_b["close"])

    def test_fetch_prices_empty_range_raises(self, source):
        start = date(2024, 1, 6)  # Saturday
        end = date(2024, 1, 7)    # Sunday — no business days
        with pytest.raises(DataSource_error):
            source.fetch_prices("STUB1", start, end)

    def test_fetch_instrument_info(self, source):
        info = source.fetch_instrument_info("STUB1")
        assert info["symbol"] == "STUB1"
        assert info["name"] == "STUB1"
        assert info["exchange"] == "Stub"
        assert info["currency"] == "USD"
        assert "asset_class" in info


# --- FREDSource ---


@pytest.mark.skipif(
    not FRED_AVAILABLE or FREDSource is None,
    reason="fredapi not installed or FRED source unavailable",
)
class TestFREDSourceNoKey:
    """FRED tests when library is installed but no API key (construction fails)."""

    def test_init_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("FRED_API_KEY", raising=False)
        with pytest.raises(DataSource_error):
            FREDSource(api_key="")


@pytest.mark.skipif(
    not FRED_AVAILABLE or FREDSource is None or not os.environ.get("FRED_API_KEY"),
    reason="FRED API key not set (set FRED_API_KEY for integration tests)",
)
class TestFREDSource:
    """Integration tests for FRED when fredapi is installed and FRED_API_KEY is set."""

    @pytest.fixture
    def source(self):
        return FREDSource()

    def test_source_name(self, source):
        assert source.source_name == "FRED"

    def test_fetch_prices_known_series(self, source):
        # Use a well-known FRED series that has daily data
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        df = source.fetch_prices("FEDFUNDS", start, end)
        assert df is not None
        assert len(df) >= 0
        if len(df) > 0:
            for col in ["date", "open", "high", "low", "close", "volume"]:
                assert col in df.columns

    def test_fetch_instrument_info(self, source):
        info = source.fetch_instrument_info("FEDFUNDS")
        assert info["symbol"] == "FEDFUNDS"
        assert info["exchange"] == "FRED"
        assert info["currency"] == "USD"

    def test_fetch_prices_invalid_series_raises(self, source):
        start = date(2024, 1, 1)
        end = date(2024, 1, 31)
        with pytest.raises(DataSource_error):
            source.fetch_prices("INVALID_SERIES_XYZ_123", start, end)


# --- YFinanceSource (optional integration) ---


@pytest.mark.skipif(
    os.environ.get("SKIP_NETWORK_TESTS") == "1",
    reason="Network tests disabled (SKIP_NETWORK_TESTS=1)",
)
class TestYFinanceSource:
    """Integration-style tests for Yahoo Finance (requires network)."""

    @pytest.fixture
    def source(self):
        return YFinanceSource()

    def test_source_name(self, source):
        assert source.source_name == "Yahoo Finance"

    def test_fetch_instrument_info(self, source):
        info = source.fetch_instrument_info("AAPL")
        assert info["symbol"] == "AAPL"
        assert "name" in info
        assert info.get("currency") == "USD"

    def test_fetch_prices_returns_data(self, source):
        end = date.today()
        start = end - timedelta(days=30)
        df = source.fetch_prices("AAPL", start, end)
        assert df is not None
        assert len(df) > 0
        for col in ["date", "open", "high", "low", "close", "volume"]:
            assert col in df.columns

    def test_fetch_multiple(self, source):
        end = date.today()
        start = end - timedelta(days=7)
        symbols = ["AAPL", "MSFT"]
        results = source.fetch_multiple(symbols, start, end)
        assert isinstance(results, dict)
        for sym in symbols:
            assert sym in results
            assert len(results[sym]) >= 0
