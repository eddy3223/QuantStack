"""
Feature engineering for quantitative analysis.

This module transforms raw price data into features used for:
- Trading signals
- ML models
- Risk analysis

Features include technical indicators, returns, volatility etc.
"""

import pandas as pd
import numpy as np
from typing import Optional 

class FeatureEngine:
    """
    Generate features from price data.

    Example:
        engine = FeatureEngine()
        features = engine.compute_all(price_df)
    """

    def compute_all(
        self,
        df: pd.DataFrame,
        include_ta: bool =True,
    ) -> pd.DataFrame:
        """
        Compute all features from OHLCV data.

        Args:
            df: DataFrame with columns: date, open, high, low, close, volume
            include_ta: Include technical analysis indicators

        Returns:
            DataFrame with original data plus feature columns
        """

        result = df.copy()

        # Ensure we have the close column
        if 'close' not in result.columns:
            raise ValueError("DataFrame must contain 'close' column")

        result = self._add_returns(result)

        result = self._add_volatility(result)

        result = self._add_moving_averages(result)

        if include_ta:
            result = self._add_technical_indicators(result)

        return result

    def _add_returns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add return calculations."""
        close = df['close']

        df['return_1d'] = close.pct_change(1)
        df['return_5d'] = close.pct_change(5)
        df['return_21d'] = close.pct_change(21)

        df['log_return_1d'] = np.log(close / close.shift(1))

        df['cumulative_return'] = (1 + df['return_1d'].fillna(0)).cumprod() - 1

        return df 

    def _add_volatility(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility calculations."""
        returns = df['log_return_1d']

        #Rolling volatility annualized
        df['volatility_21d'] = returns.rolling(21).std(ddof=0) * np.sqrt(252)
        df['volatility_63d'] = returns.rolling(63).std(ddof=0) * np.sqrt(252)

        df['realized_vol_5d'] = returns.rolling(5).std(ddof=0) * np.sqrt(252)

        return df

    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add moving average calculations."""
        close = df['close']

        # Simple Moving Averages
        df['sma_10'] = close.rolling(10).mean()
        df['sma_21'] = close.rolling(21).mean()
        df['sma_50'] = close.rolling(50).mean()
        df['sma_200'] = close.rolling(200).mean()

        # Exponential Moving Averages
        df['ema_12'] = close.ewm(span=12, adjust=False).mean()
        df['ema_26'] = close.ewm(span=26, adjust=False).mean()

        # price relative to moving averages
        df['price_to_sma_21'] = close / df['sma_21'] - 1
        df['price_to_sma_50'] = close / df['sma_50'] - 1
        df['price_to_sma_200'] = close / df['sma_200'] - 1

        # Moving average crossovers 
        df['sma_10_above_50'] = (df['sma_10'] > df['sma_50']).astype(int)
        df['sma_50_above_200'] = (df['sma_50'] > df['sma_200']).astype(int)

        return df

    def _add_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add technical analysis indicators."""
        close = df['close']
        high = df.get('high', close)
        low = df.get('low', close)

        df['rsi_14'] = self._calculate_rsi(close, 14)

        # MACD
        macd_line = df['ema_12'] - df['ema_26']
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        df['macd'] = macd_line
        df['macd_signal'] = signal_line
        df['macd_histogram'] = macd_line - signal_line

        # Bollinger Bands
        sma_20 = close.rolling(20).mean()
        std_20 = close.rolling(20).std(ddof=0)
        df['bb_upper'] = sma_20 + (2 * std_20)
        df['bb_lower'] = sma_20 - (2 * std_20)
        df['bb_position'] = (close - df['bb_lower']) / (df['bb_upper'] - df['bb_lower']) #where current price is in relation to the bands

        # Average True Range (ATR)
        df['atr_14'] = self._calculate_atr(high, low, close, 14)

        # Momentum 
        df['momentum_10'] = close / close.shift(10) - 1
        df['momentum_21'] = close / close.shift(21) - 1

        return df

    def _calculate_rsi(self, prices: pd.Series, window: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = prices.diff()

        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)

        avg_gain = gain.ewm(alpha=1/window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1/window, adjust=False).mean()

        rs = avg_gain / (avg_loss + 1e-10)
        rsi = 100 - (100 / (1 + rs))

        return rsi 

    def _calculate_atr(
        self,
        high: pd.Series,
        low: pd.Series, 
        close: pd.Series, 
        window: int = 14
    ) -> pd.Series:
        """Calculate Average True Range."""
        prev_close = close.shift(1)

        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()

        true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = true_range.ewm(alpha=1/window, adjust=False).mean()

        return atr 

    def get_feature_names(self) -> list:
        """Get list of feature names that will be generated."""
        names = []
        names.extend(['return_1d', 'return_5d', 'return_21d', 'log_return_1d', 'cumulative_return'])
        names.extend(['volatility_21d', 'volatility_63d', 'realized_vol_5d'])
        names.extend(['sma_10', 'sma_21', 'sma_50', 'sma_200'])
        names.extend(['ema_12', 'ema_26'])
        names.extend(['price_to_sma_21', 'price_to_sma_50', 'price_to_sma_200'])
        names.extend(['sma_10_above_50', 'sma_50_above_200'])
        names.extend(['rsi_14', 'macd', 'macd_signal', 'macd_histogram'])
        names.extend(['bb_upper', 'bb_lower', 'bb_position'])
        names.extend(['atr_14', 'momentum_10', 'momentum_21'])
        return names

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convenience function to computeall features.

    Args:
        df: DataFrame with columns: date, open, high, low, close, volume
    
    Returns:
        DataFrame with features added
    """
    engine = FeatureEngine()
    return engine.compute_all(df)