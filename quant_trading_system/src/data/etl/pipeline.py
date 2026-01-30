"""
ETL Pipeline for the trading system.

This module orchestrates:
1. Extract - Fetch data from sources 
2. Transform - Validate, clean and standardize
3. Load - Insert into database
"""

from datetime import date, datetime
from typing import Optional 
import pandas as pd 

from src.data.database import get_session, init_database
from src.data.models import Instrument, PriceDaily, DataLoadLog, DataLoadSymbol, AssetClass
from src.data.sources.yfinance_source import YFinanceSource
from src.data.sources.base import DataSource_error

class ETLPipeline:
    """
    Market data ETL pipeline.

    Example usage:
        pipeline = ETLPipeline()
        pipeline.run(["AAPL", "GOOG", "MSFT"], date(2023, 1, 1), date(2023, 1, 31))
    """

    def __init__(self, source=None):
        """
        Initialize the pipeline with a data source (defaults to Yahoo Finance)

        Args:
            source: DataSource instance (defaults to YFinanceSource)4
        """
        self.source = source or YFinanceSource()

    def run(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        skip_existing: bool = True,
    ) -> dict:
        """
        Run the full ETL pipeline.

        Args:
            symbols: List of instrument symbols to process
            start_date: Start date for the data extraction
            end_date: End date for the data extraction
            skip_existing: Skip symbols that already have data in the database

        Returns:
            Dict with job statistics
        """
        # Ensure database is initialized
        init_database()

        # Start logging 
        job_log = self._start_job_log(symbols, start_date, end_date)

        stats = {
            'symbols_processed': 0,
            'symbols_failed': 0,
            'records_inserted': 0,
            'records_skipped': 0,
            'status': 'RUNNING',
            'error_message': None,
            'completed_at': None,
            'started_at': datetime.now(),
        }

        try:
            for symbol in symbols:
                print(f"\nProcessing {symbol}...")

                try:
                    # Extract and Transform
                    result = self._process_symbol(symbol, start_date, end_date, skip_existing)

                    stats['records_inserted'] += result['inserted']
                    stats['records_skipped'] += result['skipped']
                    stats['symbols_processed'] += 1

                    # Log symbol success
                    self._log_symbol(job_log.id, symbol, 'SUCCESS', result['inserted'], result['skipped'])

                except DataSource_error as e:
                    print(f"  ✗ Failed: {symbol}: {e}")
                    stats['symbols_failed'] += 1
                    self._log_symbol(job_log.id, symbol, 'FAILED', 0, 0, str(e)) 

            self._complete_job_log(job_log.id, 'SUCCESS', stats['records_inserted'], stats['records_skipped'])

        except Exception as e:
            print(f"Unexpected error processing all symbols: {e}")
            stats['symbols_failed'] += 1
            self._complete_job_log(job_log.id, 'FAILED', 0, 0, str(e)) 
            raise

        return stats

    def _process_symbol(
        self,
        symbol: str,
        start_date: date,
        end_date: date,
        skip_existing: bool = True,
    ) -> dict:
        """Process a single symbol: extract, transform and load."""

        # Extract
        df = self.source.fetch_prices(symbol, start_date, end_date)
        print(f"  ✓ Extracted {len(df)} rows for {symbol} from {self.source.source_name}")

        #Ensure instrument exists in database
        instrument_id = self._ensure_instrument(symbol)

        # Transform and load
        inserted = 0
        skipped = 0

        with get_session() as session:
            for _, row in df.iterrows():
                #Check if this date already exists
                if skip_existing:
                    existing = session.query(PriceDaily).filter_by(
                        instrument_id=instrument_id,
                        date=row['date']
                    ).first()

                    if existing:
                        skipped += 1
                        continue

                # Create new price daily record
                price = PriceDaily(
                    instrument_id=instrument_id,
                    date=row['date'],
                    open=row.get('open'),
                    high=row.get('high', None),
                    low=row.get('low', None),
                    close=row.get('close', None),
                    volume=row.get('volume', None),
                    adj_close=row.get('adj_close', None),
                    source=self.source.source_name,
                )
                try:
                    session.add(price)
                    session.flush()
                    inserted += 1
                except Exception as e:
                    session.rollback()
                    skipped += 1

        print(f"    Inserted {inserted} records for {symbol}, skipped {skipped}")
        return {
            'inserted': inserted,
            'skipped': skipped,
        }

    def _ensure_instrument(self, symbol: str) -> int:
        """
        Ensure instrument exists in database, create if not.
        Returns instrument id.
        """
        with get_session() as session:
            instrument = session.query(Instrument).filter_by(symbol=symbol).first()
            if instrument:
                return instrument.id

            # get info from source and create 
            print(f"   Creating instrument record for {symbol}...")
            info = self.source.fetch_instrument_info(symbol)

            asset_class_str = info.get('asset_class', 'equity')
            asset_class = AssetClass(asset_class_str)

            instrument = Instrument(
                symbol=symbol,
                name=info.get('name', symbol),
                asset_class=asset_class,
                exchange=info.get('exchange', 'Unknown'),
                currency=info.get('currency', 'USD'),
                first_trade_date=info.get('first_trade_date', None),
                last_trade_date=info.get('last_trade_date', None),
                sector=info.get('sector', 'Unknown'),
                industry=info.get('industry', 'Unknown'),
            )
            session.add(instrument)
            session.flush() #get the id before commit 

            return instrument.id

    def _start_job_log(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date
    ) -> DataLoadLog:
        """Create a job log entry"""

        with get_session() as session:
            log = DataLoadLog(
                source=self.source.source_name,
                job_type='price_load',
                started_at=datetime.now(),
                status='RUNNING',
                records_processed=0,
            )
            session.add(log)
            session.flush()
            log_id = log.id 

        log = DataLoadLog(id=log_id)
        return log

    def _log_symbol(
        self,
        load_id: int,
        symbol: str,
        status: str,
        records: int,
        skipped: int,
        error: Optional[str] = None,
    ):
        """Log individual symbol processing"""
        with get_session() as session:
            symbol_log = DataLoadSymbol(
                load_log_id=load_id,
                symbol=symbol,
                status=status,
                records_loaded=records,
                records_skipped=skipped,
                error_message=error,
            )
            session.add(symbol_log)

    def _complete_job_log(
        self,
        load_id: int,
        status: str,
        records: int,
        skipped: int,
        error: Optional[str] = None,
    ):
        """Update the job log and update status"""
        with get_session() as session:
            log = session.query(DataLoadLog).filter_by(id=load_id).first()
            if log:
                log.completed_at = datetime.now()
                log.status = status
                log.records_processed = records
                log.error_message = error
                session.add(log)