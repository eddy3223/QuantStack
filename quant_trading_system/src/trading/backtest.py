"""
Vectorized backtesting for trading strategies.

Evaluates trading strategies using historical price data without lookahead bias.
"""

import pandas as pd
import numpy as np
from dataclasses import dataclass
import matplotlib.pyplot as plt
from typing import Optional

@dataclass
class BacktestResult:
    """Results of a backtest simulation."""
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    total_return: float
    annualized_return: float
    max_drawdown: float
    sharpe_ratio: float
    trades: pd.DataFrame
    positions: pd.DataFrame
    weights: pd.DataFrame
    signals: pd.DataFrame
    win_rate: float
    per_asset_equity: pd.DataFrame
    per_asset_cumulative_return: pd.Series
    per_asset_sharpe: pd.DataFrame
    per_asset_max_drawdown: pd.DataFrame
    per_asset_win_rate: pd.DataFrame
    equity: pd.Series

class BacktestEngine:
    """
    Vectorized backtesting engine
    Uses previous-day signals to size positions, avoids lookahead bias
    """

    def __init__(
        self,
        initial_capital: float = 100_000.0,
        target_volatility: Optional[float] = None,
        risk_free_rate: float = 0.05,
        transaction_costs: float = 0.001,
        slippage: float = 0.001,
        verbose: bool = True,
    ):
        self.initial_capital = initial_capital
        self.target_volatility = target_volatility
        self.risk_free_rate = risk_free_rate
        self.transaction_costs = transaction_costs
        self.slippage = slippage
        self.verbose = verbose

    def run(self, prices: pd.DataFrame, signals: pd.DataFrame) -> BacktestResult:
        """
        Run backtest 

        Args:
            prices: DataFrame with historical prices (columns = symbols, index = dates)
            signals: Trading signals -1,0,+1 same index as prices
        """

        if prices.shape != signals.shape:
            raise ValueError("Prices and signals must have the same shape")

        prices = prices.sort_index()
        signals = signals.reindex(prices.index).ffill().fillna(0)

        # Use previous-day signals to size positions
        # Signal at t-1 -> position at t -> PnL from return t
        raw_positions = signals.shift(1).fillna(0)
        
        # raw returns
        returns = prices.pct_change().fillna(0)

        # Apply transaction costs and slippage
        position_changes = raw_positions.diff().abs()
        costs = (self.transaction_costs + self.slippage) * position_changes
        strategy_returns = raw_positions * returns
        strategy_returns -= costs

        positions = raw_positions.copy()

        if self.target_volatility is not None:
            rolling_vol = strategy_returns.rolling(window=21).std() * np.sqrt(252)
            vol_scale = self.target_volatility / rolling_vol
            vol_scale = vol_scale.clip(0,2).fillna(1)
            strategy_returns *= vol_scale
            positions *= vol_scale
            
        # cumulative equtiy
        daily_portfolio_return = strategy_returns.mean(axis=1)
        equity = (1 + daily_portfolio_return).cumprod() * self.initial_capital

        # total return
        cumulative_return = equity.iloc[-1] / self.initial_capital - 1
        annualized_return = (1 + cumulative_return) ** (252 / len(equity)) - 1

        # Sharpe (annualized)
        excess_returns = daily_portfolio_return - (self.risk_free_rate / 252)
        sharpe = excess_returns.mean() / excess_returns.std() * np.sqrt(252)
        sharpe = sharpe if not np.isnan(sharpe) else 0

        # Max drawdown
        rolling_max = equity.cummax()
        drawdowns = (equity - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()

        # Trade count (position changes)
        trade_dates = position_changes.sum(axis=1).loc[lambda x: x!=0].index
        position_changes_df = pd.DataFrame({
            'date': trade_dates,
            'total_position_change': position_changes.sum(axis=1).loc[trade_dates],
            'equity': equity.loc[trade_dates],
        })

        # Win rate of nonzero return days
        winning_days = (daily_portfolio_return > 0).sum()
        total_trade_days = (daily_portfolio_return != 0).sum()
        win_rate = winning_days / total_trade_days if total_trade_days > 0 else 0

        # per asset metrics
        per_asset_equity = (1 + strategy_returns).cumprod() * (self.initial_capital / prices.shape[1])
        per_asset_cumulative_return = per_asset_equity.iloc[-1] / per_asset_equity.iloc[0] - 1
        per_asset_sharpe = (strategy_returns.mean() / strategy_returns.std()).mul(np.sqrt(252)).fillna(0)
        per_asset_rolling_max = per_asset_equity.cummax()
        per_asset_max_drawdown = ((per_asset_equity - per_asset_rolling_max) / per_asset_rolling_max).min()
        per_asset_win_rate = ((strategy_returns > 0).sum() / (strategy_returns != 0).sum()).fillna(0)

        if self.verbose:
            print(f"\nBacktest results:")
            print(f"  Total return: {cumulative_return:,.2%}")
            print(f"  Annualized return: {annualized_return:,.2%}")
            print(f"  Max drawdown: {max_drawdown:,.2%}")
            print(f"  Sharpe ratio: {sharpe:,.2f}")
            print(f"  Win rate: {win_rate:,.2%}")
            print(f"  Number of trades: {len(position_changes_df)}")
            print(f"  Number of days: {len(prices.index)}")
            print(f"  Initial capital: {self.initial_capital:,.2f}")
            if self.target_volatility is not None:
                print(f"  Target volatility: {self.target_volatility:,.2f}")

        return BacktestResult(
            start_date=prices.index[0],
            end_date=prices.index[-1],
            total_return=cumulative_return,
            annualized_return=annualized_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            trades=position_changes_df,
            positions=positions,
            weights=positions.div(positions.abs().sum(axis=1), axis=0),
            signals=signals,
            win_rate=win_rate,
            per_asset_equity=per_asset_equity,
            per_asset_cumulative_return=per_asset_cumulative_return,
            per_asset_sharpe=per_asset_sharpe,
            per_asset_max_drawdown=per_asset_max_drawdown,
            per_asset_win_rate=per_asset_win_rate,
            equity=equity,
        )

def run_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    initial_capital: float = 100000.0,
    target_volatility: Optional[float] = None,
    risk_free_rate: float = 0.05,
    transaction_costs: float = 0.001,
    slippage: float = 0.001,
    verbose: bool = True,
) -> BacktestResult:
    """
    Convenience function for BacktestEngine
    """
    engine = BacktestEngine(
        initial_capital=initial_capital,
        target_volatility=target_volatility,
        risk_free_rate=risk_free_rate,
        transaction_costs=transaction_costs,
        slippage=slippage,
        verbose=verbose,
    )
    return engine.run(prices, signals)


def plot_backtest_results(result: BacktestResult, show_drawdown: bool = True, show_per_asset: bool = True):
    """
    Plot portfolio per-asset equity curves and drawdowns

    Args:
        result: BacktestResult object containing metrics
        show_drawdown: Whether to show drawdown plot
        show_per_asset: Whether to show per-asset plot
    """
    plt.figure(figsize=(28,16))

    # Portfolio equity curve
    plt.plot(result.equity.index, result.equity, label = 'Portfolio Equity', color='black', linewidth=2)

    for col in result.per_asset_equity.columns:
        plt.plot(result.per_asset_equity.index, result.per_asset_equity[col], label=f'{col} Equity', linewidth=1.2, alpha = .8)

    plt.title('Portfolio and per asset equity curves')
    plt.xlabel('Date')
    plt.ylabel('Equity ($)')
    plt.legend(loc='best')
    plt.grid(True)
    plt.tight_layout()
    plt.show()

    if show_drawdown:
        plt.figure(figsize=(14,8))
        # portfolio_equtiy = result.trades['equity'].reindex(result.per_asset_equity.index).ffill()
        portfolio_drawdown = (result.equity - result.equity.cummax()) / result.equity.cummax()
        plt.plot(portfolio_drawdown.index, portfolio_drawdown, label='Portfolio Drawdown', color='red')
        plt.title('Portfolio Drawdown')
        plt.xlabel('Date')
        plt.ylabel('Drawdown (%)')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    if show_per_asset:
        plt.figure(figsize=(14,8))
        for col in result.per_asset_equity.columns:
            plt.plot(result.per_asset_equity.index, result.per_asset_equity[col], label=f'{col} Equity', linewidth=1.2, alpha = .8)
        plt.title('Per Asset Equity Curves')
        plt.xlabel('Date')
        plt.ylabel('Equity ($)')
        plt.legend(loc='best')
        plt.grid(True)
        plt.tight_layout()
        plt.show()
        