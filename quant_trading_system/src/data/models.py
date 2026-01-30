"""
Database models for market data storage.

This module defines the SQL schema for strogin:
- Instrumtents (stocks, ETFs, futures, etc.)
- Price data (OHLCV)
- Corporate actions (splits, dividends, etc.)

Design decisions:
- Normalized schema to avoid data duplication
- Timestamps in UTC for consistency
- Separate tables for different data frequencies 
"""

from datetime import datetime 

from sqlalchemy import(
    Column, Integer, String, Float, DateTime, Date, 
    ForeignKey, Index, UniqueConstraint, Enum, Boolean, BigInteger, Text
)
from sqlalchemy.orm import declarative_base, relationship
import enum 

Base = declarative_base()

class AssetClass(enum.Enum):
    """Supported asset classes."""
    EQUITY = "equity"
    ETF = "etf"
    FUTURE = "future"
    OPTION = "option"
    FOREX = "forex" 
    CRYPTO = "crypto"

class Instrument(Base):
    """ 
    Master table for all tradeable instruments.

    This is the 'single source of truth' for all instrument metadata.
    All other tables reference this via foreign key.
    """

    __tablename__ = "instruments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True)
    name = Column(String(200), nullable=False)
    asset_class = Column(Enum(AssetClass), nullable=False)
    exchange = Column(String(50))
    currency = Column(String(3), default="USD")

    # Lifecycle tracking 
    is_active = Column(Boolean, default=True)
    first_trade_date = Column(Date)
    last_trade_date = Column(Date)

    # Metadata
    sector = Column(String(100))
    industry = Column(String(100))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    prices = relationship("PriceDaily", back_populates="instrument")

    def __repr__(self):
        return f"<Insturment(symbol='{self.symbol}', asset_class='{self.asset_class.value}')>"

class PriceDaily(Base):
    """
    Daily OHLCV price data for instruments.

    Indexed by (instrument_id, date) for efficient querying.
    Stores adjusted prices to account for splits and dividends.
    """

    __tablename__ = "prices_daily"

    id = Column(Integer, primary_key=True, autoincrement=True)
    instrument_id = Column(Integer, ForeignKey("instruments.id"), nullable=False)
    date = Column(Date, nullable=False)

    # OHLCV data
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(BigInteger)

    # Adjusted close (accounts for splits and dividends)
    adj_close = Column(Float)

    # Data quality
    source = Column(String(50))

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    instrument = relationship("Instrument", back_populates="prices")

    # Constraints
    __table_args__ = (
        UniqueConstraint("instrument_id", "date", name="uq_instrument_date"),
        Index("idx_prices_date", "date"),
        Index("idx_prices_instrument_date", "instrument_id", "date"),
    )

class DataLoadLog(Base):
    """
    Tracks ETL job runs for auditing and debugging.

    This is crucial for production systems to track when data was loaded and if there
    were any issues.
    """

    __tablename__ = "data_load_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    source = Column(String(50), nullable=False)
    job_type = Column(String(50), nullable=False)
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    status = Column(String(50), nullable=False)
    records_processed = Column(Integer)
    error_message = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship to symbols (one-to-many) 
    symbols = relationship("DataLoadSymbol", back_populates="load_log")

class DataLoadSymbol(Base):
    """
    Symbols processed in each ETL job.

    Normalized design - allows querying:
    - When was symbol loaded?
    - Which jobs included this symbol?
    """

    __tablename__ = "data_load_symbols"

    id = Column(Integer, primary_key=True, autoincrement=True)
    load_log_id = Column(Integer, ForeignKey("data_load_log.id"), nullable=False)
    symbol = Column(String(20), nullable=False)

    status = Column(String(50), nullable=False)
    records_loaded = Column(Integer)
    records_skipped = Column(Integer)
    error_message = Column(Text)

    load_log = relationship("DataLoadLog", back_populates="symbols")

    __table_args__ = (
        UniqueConstraint("load_log_id", "symbol", name="uq_load_log_symbol"),
        Index("idx_load_symbol_symbols", "symbol"),
    )
    