import streamlit as st 
from src.data.database import get_session, init_database
from src.data.models import Instrument, PriceDaily
from src.data.sources.stub_source import StubSource
from src.data.sources.fred_source import FREDSource
from src.data.sources.yfinance_source import YFinanceSource
from src.data.sources.base import DataSource_error
from src.data.etl.pipeline import ETLPipeline
from src.analytics.features import FeatureEngine
from src.analytics.signals import SignalCombiner, MomentumSignal, RSISignal, MACDSignal
from src.trading.backtest import BacktestEngine, run_backtest, plot_backtest_results
from src.trading.diagnostics import DiagnosticEngine
from datetime import datetime, timedelta, date
import traceback
from src.trading.backtest_helpers import load_multi_asset_prices, build_signals_for_symbol
import pandas as pd

init_database()
st.sidebar.title("QuantPlatform - Systematic Trading Data Platform")
page = st.sidebar.radio("Go to", ["Data", "Backtest", "Analytics"])

if page == "Data":
    st.write("Data page -- list instruments, load data, query prices")
    with get_session() as session:
        instruments = session.query(Instrument).all()
        if not instruments:
            st.error("No instruments found in database. Run: poetry run python scripts/cli.py data load AAPL MSFT --days 252")
        else:
            st.write(f"Found {len(instruments)} instruments:")
            symbol = st.selectbox("Select a symbol", [inst.symbol for inst in instruments])
            if symbol:
                st.write(f"Selected symbol: {symbol}")
                instrument = session.query(Instrument).filter(Instrument.symbol == symbol).first()
                if not instrument:
                    st.error(f"Instrument {symbol} not found in database")
                else:
                    price_rows = session.query(PriceDaily).filter(PriceDaily.instrument_id == instrument.id).order_by(PriceDaily.date).all()
                    if not price_rows:
                        st.error("No price data found for this symbol")
                    else:
                        st.write(f"Found {len(price_rows)} price records for {symbol}")
                        price_df = pd.DataFrame([
                            {"date": p.date, "open": p.open, "high": p.high, "low": p.low, "close": p.close, "volume": p.volume}
                            for p in price_rows
                        ])
                        price_df = price_df.set_index("date").sort_index()
                        st.line_chart(price_df[["close"]])

    st.subheader("Load Data")
    if st.session_state.get('last_load_stats'):
        st.write("Last load stats:")
        st.write(st.session_state['last_load_stats'])
        st.write(f"Symbols processed: {st.session_state['last_load_stats']['symbols_processed']}")
        st.write(f"Records inserted: {st.session_state['last_load_stats']['records_inserted']}")
        st.write(f"Records skipped: {st.session_state['last_load_stats']['records_skipped']}")
        st.write(f"Symbols failed: {st.session_state['last_load_stats']['symbols_failed']}")
        st.write(f"Total records: {st.session_state['last_load_stats']['records_inserted'] + st.session_state['last_load_stats']['records_skipped']}")
        st.write(f"Status: {st.session_state['last_load_stats']['status']}")
        st.write(f"Error message: {st.session_state['last_load_stats']['error_message']}")
        st.write(f"Completed at: {st.session_state['last_load_stats']['completed_at']}")
        st.write(f"Started at: {st.session_state['last_load_stats']['started_at']}")
    results =st.text_input("Symbols (comma separated):", value = "AAPL, MSFT, GOOGL")
    days = st.number_input("Days of history:", value = 365, min_value = 1, max_value = 3650)
    if st.button("Load Data"):
        del st.session_state['last_load_stats']
        try:
            symbols = [s.strip() for s in results.split(",")]
            if not symbols:
                st.error("No symbols provided") 
                raise ValueError("No symbols provided")
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            pipeline = ETLPipeline()
            stats = pipeline.run(symbols, start_date, end_date)
            st.session_state['last_load_stats'] = stats
            st.rerun()

        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.error(traceback.format_exc())
        
elif page == "Backtest":
    st.write("Backtest page -- pick symbols, dates, run backtest, view results")
    with get_session() as session:
        instruments = session.query(Instrument).all()
        if not instruments:
            st.error("No instruments found in database. Run: poetry run python scripts/cli.py data load AAPL MSFT --days 252")
        else:
            st.write(f"Found {len(instruments)} instruments:")
            symbol_options = [inst.symbol for inst in instruments]
            symbols = st.multiselect("Select symbols", symbol_options, default=symbol_options[:3] if len(symbol_options) >= 3 else symbol_options)
    start_date = st.date_input("Start date", value=date.today() - timedelta(days=365))
    end_date = st.date_input("End date", value=date.today())
    initial_capital = st.number_input("Initial capital", value=100000, min_value=10000, max_value=1000000000)
    target_volatility = st.number_input("Target volatility", value=0.02, min_value=0.0001, max_value=0.1)
    risk_free_rate = st.number_input("Risk free rate", value=0.05, min_value=0.0001, max_value=0.1)
    transaction_costs = st.number_input("Transaction costs", value=0.001, min_value=0.0, max_value=0.1)
    slippage = st.number_input("Slippage", value=0.001, min_value=0.0, max_value=0.1)
    verbose = st.checkbox("Verbose", value=False)
    if st.button("Run Backtest"):
        try:
            if not symbols:
                st.error("Select at least one symbol")
            else:
                with get_session() as session:
                    instruments = session.query(Instrument).filter(Instrument.symbol.in_(symbols)).all()
                    if not instruments:
                        st.error("No instruments found in database for selected symbols")
                    else:
                        price_df = load_multi_asset_prices(session, instruments, symbols)
                        if price_df is None or price_df.empty:
                            st.error("No price data found for any symbol. Load data first.")
                        else:
                            price_df = price_df.dropna().sort_index()
                            price_df = price_df.loc[start_date:end_date]
                            if price_df.empty:
                                st.error("No price data in selected date range")
                            else:
                                engine = FeatureEngine()
                                signal_combiner = SignalCombiner(
                                    signals={
                                        "momentum": MomentumSignal(window=21),
                                        "rsi": RSISignal(oversold=30, overbought=70),
                                        "macd": MACDSignal(),
                                    }
                                )
                                signals_df = pd.DataFrame(
                                    {sym: build_signals_for_symbol(engine, price_df[sym], signal_combiner) for sym in price_df.columns}
                                )
                                signals_df = signals_df.reindex(price_df.index).ffill().fillna(0)

                                bt_engine = BacktestEngine(
                                    initial_capital=initial_capital,
                                    target_volatility=target_volatility,
                                    risk_free_rate=risk_free_rate,
                                    transaction_costs=transaction_costs,
                                    slippage=slippage,
                                    verbose=verbose,
                                )
                                result = bt_engine.run(price_df, signals_df)
                                st.session_state["last_backtest_result"] = result

                                st.success("Backtest completed")
                                st.subheader("Metrics")
                                col1, col2, col3, col4 = st.columns(4)
                                with col1:
                                    st.metric("Total return", f"{result.total_return:.2%}")
                                with col2:
                                    st.metric("Sharpe ratio", f"{result.sharpe_ratio:.2f}")
                                with col3:
                                    st.metric("Max drawdown", f"{result.max_drawdown:.2%}")
                                with col4:
                                    st.metric("Win rate", f"{result.win_rate:.2%}")
                                st.write(f"Trading days: {len(result.equity)} | Trades: {len(result.trades)}")
        except Exception as e:
            st.error(f"Error running backtest: {str(e)}")
            st.error(traceback.format_exc())
elif page == "Analytics":
    st.write("Analytics — equity curve, drawdown, and metrics from last backtest")
    result = st.session_state.get("last_backtest_result")
    if result is None:
        st.info("Run a backtest on the Backtest page first.")
    else:
        diag = DiagnosticEngine(result)
        report = diag.report()

        st.subheader("Metrics")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total return", f"{result.total_return:.2%}")
        with col2:
            st.metric("Sharpe ratio", f"{result.sharpe_ratio:.2f}")
        with col3:
            st.metric("Max drawdown", f"{result.max_drawdown:.2%}")
        with col4:
            st.metric("Win rate", f"{result.win_rate:.2%}")
        st.caption(f"Period: {result.start_date} to {result.end_date} | Trading days: {len(result.equity)} | Trades: {len(result.trades)}")

        with st.expander("Risk & diagnostics report"):
            pct_keys = ("total_return", "annualized_return", "max_drawdown", "win_rate")
            for key, value in report.items():
                if hasattr(value, "strftime"):
                    st.write(f"**{key}**: {value}")
                elif key in pct_keys and isinstance(value, (int, float)):
                    st.write(f"**{key}**: {value:.2%}")
                else:
                    st.write(f"**{key}**: {value}")

        st.subheader("Portfolio equity")
        st.line_chart(result.equity.to_frame("equity"))

        st.subheader("Drawdown")
        drawdown = (result.equity - result.equity.cummax()) / result.equity.cummax()
        st.line_chart(drawdown.to_frame("drawdown"))

        st.subheader("Per-asset equity")
        st.line_chart(result.per_asset_equity)

