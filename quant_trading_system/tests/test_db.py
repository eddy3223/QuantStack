"""Quick tests for database functionality."""

import sys 
sys.path.insert(0, ".")

from datetime import datetime
from src.data.database import init_database, get_session, drop_database
from src.data.models import Instrument, AssetClass

# Create all tables
print("Initializing database...")
init_database()

# Insert test record 
print("\nInserting test record...")
with get_session() as session:
    # check if ticker exists
    existing = session.query(Instrument).filter(Instrument.symbol == "AAPL").first()

    if existing:
        print(f"AAPL already exists: {existing}")
    else:
        new_instrument = Instrument(
            symbol="AAPL",
            name="Apple Inc.",
            asset_class=AssetClass.EQUITY,
            exchange="NASDAQ",
            currency="USD",
            is_active=True,
            first_trade_date=datetime(1980, 12, 12),
            last_trade_date=datetime(2025, 12, 31),
            sector="Technology",
        )
        session.add(new_instrument)
        print("Inserted AAPL")


# Query it back
print("\nQuerying test record...")
with get_session() as session:
    instruments = session.query(Instrument).all()
    for inst in instruments:
        print(f"   -   {inst.symbol}: {inst.name} ({inst.asset_class.value})")

# Drop the database
print("\nDropping database...")
drop_database()

print("\nDone!") 