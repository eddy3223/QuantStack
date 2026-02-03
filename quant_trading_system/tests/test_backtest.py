"""Test the backtesting engine with single- and multi-asset data."""

import sys
sys.path.insert(0, ".")

import pandas as pd
from src.trading.backtest import BacktestEngine, run_backtest, plot_backtest_results
from src.trading.backtest_helpers import load_multi_asset_prices, build_signals_for_symbol
from src.data.database import get_session, init_database
from src.data.models import Instrument, PriceDaily
from src.analytics.features import FeatureEngine
from src.analytics.signals import MomentumSignal, RSISignal, MACDSignal, SignalCombiner

# Symbols to backtest (must exist in DB; load first: quant data load AAPL MSFT --days 252)
SYMBOLS = ["AAPL", "MSFT", "GOOG", "AMZN", "TSLA", "NVDA", "META", "NFLX", "DIS", "CMCSA", "PEP", "ABNB", "WMT", "JPM", "V", "MA", "T", "KO", "UNH", "JNJ", "XOM", "CVX", "PG", "LLY", "MRK", "ABBV", "MDY", "QQQ", "IWM", "EEM", "EEV", "FXI", "EWZ", "EWJ", "EWG", "EWU", "EWT", "EWC", "EWH", "EWI", "EWP", "EWS", "EWT", "EWC", "EWH", "EWI", "EWP", "EWS"]


if __name__ == "__main__":
    init_database()

    with get_session() as session:
        instruments = (
            session.query(Instrument)
            .filter(Instrument.symbol.in_(SYMBOLS))
            .all()
        )
        if not instruments:
            raise ValueError(
                f"None of {SYMBOLS} found in database. Run: poetry run python scripts/cli.py data load AAPL MSFT --days 252"
            )

        price_df = load_multi_asset_prices(session, instruments, SYMBOLS)
        if price_df is None or price_df.empty:
            raise ValueError("No price data for any symbol.")

        # Align on common dates and drop rows with missing prices
        price_df = price_df.dropna()

        # Combined signal: momentum + RSI + MACD (equal weight). Applied per asset.
        engine = FeatureEngine()
        signal_combiner = SignalCombiner(
            signals={
                "momentum": MomentumSignal(window=21),
                "rsi": RSISignal(oversold=30, overbought=70),
                "macd": MACDSignal(),
            }
        )
        signals_df = pd.DataFrame(
            {
                sym: build_signals_for_symbol(engine, price_df[sym], signal_combiner)
                for sym in price_df.columns
            }
        )
        signals_df = signals_df.reindex(price_df.index).ffill().fillna(0)

        assert price_df.shape == signals_df.shape, (
            f"price_df {price_df.shape} vs signals_df {signals_df.shape}"
        )

        backtest_engine = BacktestEngine()
        backtest_result = backtest_engine.run(price_df, signals_df)
        plot_backtest_results(backtest_result, show_drawdown=True, show_per_asset=True)
