"""
Helpers for loading price data and building signals for backtests.

Used by the Streamlit app and by test/script backtest runs.
"""

import pandas as pd

from src.data.models import PriceDaily


def load_multi_asset_prices(session, instruments, symbols):
    """Load close prices for multiple symbols into a DataFrame (columns=symbols, index=date)."""
    close_dfs = []
    for inst in instruments:
        if inst.symbol not in symbols:
            continue
        rows = (
            session.query(PriceDaily)
            .filter(PriceDaily.instrument_id == inst.id)
            .order_by(PriceDaily.date)
            .all()
        )
        if not rows:
            continue
        close_dfs.append(
            pd.DataFrame(
                {"date": [r.date for r in rows], inst.symbol: [r.close for r in rows]}
            ).set_index("date")
        )
    if not close_dfs:
        return None
    return pd.concat(close_dfs, axis=1).sort_index().ffill().bfill().dropna(how="all")


def build_signals_for_symbol(engine, close_series, signal_gen):
    """Compute features and generate signal for one symbol's close series."""
    df = close_series.to_frame(name="close")
    features = engine.compute_all(df)
    return signal_gen.generate(features)
