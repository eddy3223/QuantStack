import pandas as pd 

class VectorizedBacktestEngine:
    def __init__(
        self, 
        market_data, 
        instruments,
        vol_window: int = 20,
        target_gross_exposure: float = 1.0
    ):
        self.market_data = market_data 
        self.instruments = instruments 
        self.vol_window = vol_window 
        self.target_gross_exposure= target_gross_exposure

    def run(self, signals: pd.DataFrame) -> dict:
        """
        Run a smiple vectorized backtest
        """

        prices = self.market_data.get_close()
        returns = prices.pct_change()

        vol = self._estimate_volatility(returns) 
        positions = self._build_positions(signals)

        # --- Sanity checks ---
        assert prices.index.equals(signals.index) "Prices and signals must share the same index"
        assert set(prices.columns) == set(signals.columns) "Prices and signals must have same symbols"

        assert not positions.isna().any().any() "Positions contain NaNs"
        assert not (positions.abs() == float("inf")).any().any() "Positions contain infinite values"
        assert (positions.abs().sum(axis=1) > 0).all() "Gross exposure is zero for some dates"

        pnl = positions.shift(1) * returns 

        return {
            "positions": positions,
            "pnl": pnl,
            "portfolio_pnl": pnl.sum(axis=1),
            "volatility": vol
        }

    def _estimate_volatility(self, returns: pd.DataFrame) -> pd.DataFrame:
        return returns.rolling(self.vol_window).std()

    def _build_positions(
        self,
        signals: pd.DataFrame,
        vol: pd.DataFrame,
    ) -> pd.DataFrame:
        scaled = signals / vol 
        gross = scaled.abs().sum(axis=1)

        positions = scaled.mul(
            self.target_gross_exposure / gross, axis=0
        )
        return positions.fillna(0.0)