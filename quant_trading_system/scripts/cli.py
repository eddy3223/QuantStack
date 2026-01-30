"""
QuantPlatform Command Line Interface.

A professional CLI for managing the trading data platform.

Usage:
    quant data load APPL MSFT GOOGL --days 30
    quant data list 
    quant data status
"""

import sys
sys.path.insert(0, ".")

import click 
from datetime import date, timedelta
from tabulate import tabulate

from src.data.database import get_session, init_database
from src.data.models import Instrument, PriceDaily, DataLoadLog, DataLoadSymbol
from src.data.etl.pipeline import ETLPipeline

@click.group()
@click.version_option(version="0.1.0", prog_name="QuantPlatform")
def cli():
    """
    QuantPlatform - Systematic Trading Data Platform

    A professional data pipeline for quantitative trading.
    """
    pass 

# ============================================================
# DATA COMMANDS
# ============================================================
@cli.group()
def data():
    """Manage market data and ETL operations."""
    pass

@data.command("load")
@click.argument("symbols", nargs=-1, required=True)
@click.option("--days", type=int, default=30, help="Days of history to load")
@click.option("--start-date", default=None, type=click.DateTime(formats=["%Y-%m-%d"]), help="Start date for data loading")
@click.option("--end-date", default=None, type=click.DateTime(formats=["%Y-%m-%d"]), help="End date for data loading")
@click.option("--skip-existing", is_flag=True, help="Skip symbols that already have data")
def load_data(symbols, days, start_date, end_date, skip_existing):
    """
    Load price data for symbols.
    
    Examples:
    
        quant data load AAPL MSFT GOOGL
        
        quant data load SPY --days 365
        
        quant data load AAPL --start 2024-01-01 --end 2024-12-31
    """
    # Parse dates
    if end_date:
        end_date = end_date.date()
    else:
        end_date = date.today()

    if start_date:
        start_date = start_date.date()
    else:
        start_date = end_date - timedelta(days=days)
    
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Loading data for : {', '.join(symbols)}")
    click.echo(f"Date range: {start_date} to {end_date}")
    click.echo(f"{'=' * 60}")

    # Validate dates
    if start_date > end_date:
        click.echo(f"Error: Start date cannot be after end date")
        return
    
    # Run the pipeline
    pipeline = ETLPipeline()
    stats = pipeline.run(list(symbols), start_date, end_date, skip_existing=skip_existing)

    # Print results
    click.echo(f"\n{'=' * 60}")
    click.echo(f"Pipeline Results:")
    click.echo(f"{'=' * 60}")
    click.echo(f"Symbols processed: {stats['symbols_processed']}")
    click.echo(f"Records inserted: {stats['records_inserted']}")
    click.echo(f"Records skipped: {stats['records_skipped']}")
    click.echo(f"Symbols failed: {stats['symbols_failed']}")
    click.echo(f"Total records: {stats['records_inserted'] + stats['records_skipped']}")

@data.command("list")
@click.option("--prices", is_flag=True, help="List price data for symbols")
def data_list(prices):
    """
    List all instruments in database.

    Examples:
        quant data list
        quant data list --prices
    """
    init_database()

    with get_session() as session:
        instruments = session.query(Instrument).order_by(Instrument.symbol).all()

        if not instruments:
            click.echo(f"No instruments found in database.")
            return 

        rows = []
        for inst in instruments:
            row = [
                inst.symbol,
                inst.name[:30] + '...' if len(inst.name) > 30 else inst.name,
                inst.asset_class.value,
                inst.sector or "-",
            ]
    
            if prices:
                count = session.query(PriceDaily).filter_by(instrument_id=inst.id).count()
                row.append(count)

            rows.append(row)

        # Print table
        headers = ["Symbol", "Name", "Asset Class", "Sector"]
        if prices:
            headers.append("Days")

        click.echo()
        click.echo(tabulate(rows, headers=headers, tablefmt="simple_grid"))
        
@data.command("status")
@click.option("--limit", default=10, help="Number of recent jobs to show")
def data_status(limit):
    """
    Show recent ETL job status.

    Examples:
        quant data status
        quant data status --limit 20
    """

    init_database()

    with get_session() as session:
        jobs = session.query(DataLoadLog).order_by(DataLoadLog.id.desc()).limit(limit).all()

        if not jobs:
            click.echo(f"No job logs found in database.")
            return 

        rows = []
        for log in jobs:
            symbols = session.query(DataLoadSymbol).filter_by(load_log_id=log.id).all()
            symbol_list = ", ".join([s.symbol for s in symbols[:5]])
            if len(symbols) > 5:
                symbol_list += f", +{len(symbols) - 5} more"

            rows.append([
                log.id,
                log.status,
                log.started_at.strftime("%Y-%m-%d %H:%M:%S") if log.started_at else "-",
                log.completed_at.strftime("%Y-%m-%d %H:%M:%S") if log.completed_at else "-",
                log.records_processed,
                symbol_list,
                log.error_message[:50] + "..." if log.error_message else "-",
            ])

        headers = ["ID", "Status", "Started", "Completed", "Records", "Symbols", "Error"]
        click.echo()
        click.echo(tabulate(rows, headers=headers, tablefmt="simple_grid"))
        click.echo()

@data.command("query") 
@click.argument("symbol")
@click.option("--days", default = 10, help="Number of recent days to show")
def data_query(symbol, days):
    """
    Query price data for a symbol

    Examples:
        quant data query AAPL
        quant data query AAPL --days 30
    """
    init_database()

    with get_session() as session:
        instrument = session.query(Instrument).filter_by(symbol=symbol).first()

        if not instrument:
            click.echo(f"Error: Symbol {symbol} not found in database.")
            return

        #Get prices
        prices = (
            session.query(PriceDaily)
            .filter_by(instrument_id=instrument.id)
            .order_by(PriceDaily.date.desc())
            .limit(days)
            .all()
        )

        if not prices:
            click.echo(f"No price data found for {symbol}.")
            return

        click.echo(f"\n{symbol} - {instrument.name}")
        click.echo(f"{'=' * 60}")

        rows = []
        for p in reversed(prices):
            rows.append([
                p.date.strftime("%Y-%m-%d"),
                f"${p.open:,.2f}" if p.open else "-",
                f"${p.high:,.2f}" if p.high else "-",
                f"${p.low:,.2f}" if p.low else "-",
                f"${p.close:,.2f}" if p.close else "-",
                f"{p.volume:,.0f}" if p.volume else "-",
                f"${p.adj_close:,.2f}" if p.adj_close else "-",
            ])

        headers = ["Date", "Open", "High", "Low", "Close", "Volume", "Adj Close"]
        click.echo()
        click.echo(tabulate(rows, headers=headers, tablefmt="simple_grid"))


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Main entry point for the CLI."""
    cli()
     
if __name__ == "__main__":
    main()