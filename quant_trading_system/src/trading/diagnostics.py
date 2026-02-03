"""
Diagnostic tools for backtesting.
Computes risk and diagnostics from backtest results.
"""

import pandas as pd
from src.trading.backtest import BacktestResult

class DiagnosticEngine:
    """
    Diagnostic engine for backtesting.
    Computes risk and diagnostics from backtest results.
    """

    def __init__(self, result: BacktestResult):
        self.result = result

    def max_drawdown_duration(self) -> int:
        """
        Duration of the maximum drawdown event in trading days (peak to trough).
        Finds the date when drawdown was worst, then the last peak before it; returns days between.
        """
        equity = self.result.equity
        rolling_max = equity.cummax()
        drawdowns = (equity - rolling_max) / rolling_max
        trough_date = drawdowns.idxmin()
        peak_date = equity.loc[:trough_date].idxmax()
        return int((equity.index.get_loc(trough_date) - equity.index.get_loc(peak_date)))

    def longest_drawdown_run_days(self) -> int:
        """
        Longest contiguous run of trading days below the running peak (any drawdown period).
        Can span most of the backtest if equity never makes a new high after an early peak.
        """
        equity = self.result.equity
        rolling_max = equity.cummax()
        drawdowns = (equity - rolling_max) / rolling_max
        in_drawdown = drawdowns < 0
        period_id = (in_drawdown != in_drawdown.shift()).cumsum()
        days_per_run = in_drawdown.groupby(period_id).sum()
        return int(days_per_run.max()) if len(days_per_run) else 0

    def turnover(self, annualize: bool = True) -> float:
        """
        Average daily turnover (sum of absolute position changes across assets).
        If annualize=True, returns mean daily turnover * 252.
        """
        pos = self.result.positions
        daily_turnover = pos.diff().abs().sum(axis=1).fillna(0)
        mean_daily = daily_turnover.mean()
        return mean_daily * 252 if annualize else mean_daily

    def report(self) -> dict:
        """
        Summary diagnostics as a dict (total return, Sharpe, max DD, DD duration, win rate, turnover, etc.).
        """
        r = self.result
        return {
            "total_return": r.total_return,
            "annualized_return": r.annualized_return,
            "sharpe_ratio": r.sharpe_ratio,
            "max_drawdown": r.max_drawdown,
            "max_drawdown_duration_days": self.max_drawdown_duration(),
            "longest_drawdown_run_days": self.longest_drawdown_run_days(),
            "win_rate": r.win_rate,
            "turnover_annualized": self.turnover(annualize=True),
            "num_trades": len(r.trades),
            "num_days": len(r.equity),
            "start_date": r.start_date,
            "end_date": r.end_date,
        }
