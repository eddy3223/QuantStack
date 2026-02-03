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
from datetime import datetime, timedelta, date

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
                    price_df = session.query(PriceDaily).filter(PriceDaily.instrument_id == instrument.id).all()
                if not price_df:
                    st.error("No price data found for this symbol")
                else:
                    st.write(f"Found {len(price_df)} price records for {symbol}")

    st.subheader("Load Data")
    results =st.text_input("Symbols (comma separated):", value = "AAPL, MSFT, GOOGL")
    days = st.number_input("Days of history:", value = 365, min_value = 1, max_value = 3650)
    if st.button("Load Data"):
        try:
            symbols = [s.strip() for s in results.split(",")]
            if not symbols:
                st.error("No symbols provided") 
                raise ValueError("No symbols provided")
            end_date = date.today()
            start_date = end_date - timedelta(days=days)
            pipeline = ETLPipeline()
            stats = pipeline.run(symbols, start_date, end_date)
            st.write(stats)
            st.write(f"Pipeline Results:")
            st.write(f"Symbols processed: {stats['symbols_processed']}")
            st.write(f"Records inserted: {stats['records_inserted']}")
            st.write(f"Records skipped: {stats['records_skipped']}")
            st.write(f"Symbols failed: {stats['symbols_failed']}")
            st.write(f"Total records: {stats['records_inserted'] + stats['records_skipped']}")
            st.write(f"Status: {stats['status']}")
            st.write(f"Error message: {stats['error_message']}")
            st.write(f"Completed at: {stats['completed_at']}")
            st.write(f"Started at: {stats['started_at']}")
            st.rerun()

        except Exception as e:
            st.error(f"Error loading data: {str(e)}")
            st.error(traceback.format_exc())
        
elif page == "Backtest":
    st.write("Backtest page -- pick symbols, dates, run backtest, view results")
elif page == "Analytics":
    st.write("Results page -- equity curve and metrics")

