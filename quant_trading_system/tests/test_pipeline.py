"""Test the ETL pipeline - full end-to-end test."""

import sys 
sys.path.insert(0, ".")

from datetime import date, timedelta
from src.data.etl.pipeline import ETLPipeline
from src.data.database import get_session, init_database 
from src.data.models import Instrument, PriceDaily, DataLoadLog, DataLoadSymbol

print("=" * 60)
print("Testing ETL Pipeline")
print("=" * 60)

# initialize 
pipeline = ETLPipeline()

# test with some symbols 
symbols = ["AAPL", "GOOG", "MSFT", "AMZN", "TSLA"]
end_date = date.today()
start_date = end_date - timedelta(days=60)

print(f"\nLoading data for {symbols}")
print(f"Date range: {start_date} to {end_date}")

# run the pipeline
stats = pipeline.run(symbols, start_date, end_date, skip_existing=False)

print("\n" + "=" * 60)
print("PIPELINE RESULTS")
print("=" * 60)
print(f"   Symbols processed: {stats['symbols_processed']}")
print(f"   Records inserted: {stats['records_inserted']}")
print(f"   Records skipped: {stats['records_skipped']}")
print(f"   Symbols failed: {stats['symbols_failed']}")
print(f"   Total records: {stats['records_inserted'] + stats['records_skipped']}")
print(f"   Status: {stats['status']}")
print(f"   Error message: {stats['error_message']}")
print(f"   Completed at: {stats['completed_at']}")
print(f"   Started at: {stats['started_at']}")
print(f"   Source: {pipeline.source.source_name}")

#verify in database
print("\n" + "=" * 60)
print("DATABASE CONTENTS")
print("=" * 60)

with get_session() as session:
    # check instruments
    instruments = session.query(Instrument).all()
    print(f"\nInstruments ({len(instruments)}):")
    for inst in instruments:
        print(f"  - {inst.symbol}: {inst.name} ({inst.asset_class.value})")

    #check price counts per symbol
    print(f"\nPrice counts per symbol:")
    for inst in instruments:
        count = session.query(PriceDaily).filter_by(instrument_id=inst.id).count()
        print(f"  - {inst.symbol}: {count} days")

    #check job log
    logs = session.query(DataLoadLog).order_by(DataLoadLog.started_at.desc()).limit(5).all()
    print(f"\nRecent job logs:")
    for log in logs:
        print(f"  - Job {log.id} ({log.status}): {log.records_processed} records, {log.completed_at}")

# run again to test skip_existing
print("\n" + "=" * 60)
print("TESTING IDEMPOTENCY (re-run with skip_existing=True)")
print("=" * 60)
stats2 = pipeline.run(symbols, start_date, end_date, skip_existing=True)
print(f"   Records inserted (second run): {stats2['records_inserted']} (should be 0)")
print(f"   Records skipped (second run): {stats2['records_skipped']} (should match previous run)")

print("\n" + "=" * 60)
print("✓ Pipeline test complete!")
print("=" * 60)