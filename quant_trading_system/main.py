import matplotlib.pyplot as plt 
from core.market_data import MarketData
from backtest.engine import VectorizedBacktestEngine
from signals.momentum import momentum_signal
from backets.diagnostics import check_gross_exposure

def main():
    market_data = MarketData(
        {
            "SPY": spy_df,
            "TLT": tlt_df,
        }
    )

    prices = (
        market_data
        .get("SPY")[["close"]]
        .rename(columns={"close":"SPY"})
        .join(
            market_data.get("TLT")[["close"]]
            .rename(columns={"close": "TLT"}),
            how="inner"
        )
    )

    signals = momentum_signal(prices, window=60)

    engine = VectorizedBacktestEngine(
        market_data=market_data,
        instruments=None
        vol_window=20
        target_gross_exposure=1.0
    )

    results = engine.run(signals) 
    ok = check_gross_exposure(results["positions"], target=1.0)
    print(f"Exposure OK % {ok.mean():.2%}")

    results["positions"].abs().sum(axis=1).plot(title="Gross Exposure Over Time")
    plt.axhline(1.0, color= "red", linestyle="--")
    plt.show()

    results["portfolio_pnl"].cumsum().plot(
        title="Cumulative PnL"
    )
    plt.show()

if __name__ == "__main__":
    main()