"""
Signal generation for trading strategies.

Converts features into actionable signals: +1 (long) 0 neutral -1 (short)
"""

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod
from typing import Dict, Optional

class SignalBase(ABC):
    """Abstract base class for signal generators."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return name of this signal."""
        pass

    @abstractmethod
    def generate(self, features: pd.DataFrame) -> pd.Series:
        """
        Generate signals from feature DataFrame

        Args: 
            df: DataFrame with computed features

        Returns:
            Series with +1, 0, -1 values
        """
        pass 

class MomentumSignal(SignalBase):
    """Long when price above SMA, short when below"""

    def __init__(self, window: int = 21):
        self.window = window

    @property 
    def name(self) -> str:
        return f"Momentum_{self.window}"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Generate signals based on price relative to SMA."""
        if 'sma_21' not in df.columns or 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'sma_21' and 'close' columns")

        sma_col = f'sma_{self.window}' if 'sma_{self.window}' in df.columns else 'sma_21'
        sma = df[sma_col]
        close = df['close']
        signal = np.sign(close - sma)
        signal = signal.replace(0, np.nan).fillna(0).astype(int)

        return signal

class RSISignal(SignalBase):
    """Long when oversold (RSI < 30), short when overbought (RSI > 70)"""

    def __init__(self, oversold: float = 30, overbought: float = 70):
        self.oversold = oversold
        self.overbought = overbought

    @property
    def name(self) -> str:
        return "RSI"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        if 'rsi_14' not in df.columns:
            raise ValueError("DataFrame must contain 'rsi_14'. Run FeatureEngine with include_ta = True first.")

        rsi = df['rsi_14']

        # +1 oversold (buy), -1 overbought (sell), 0 neutral
        signal = pd.Series(0, index=df.index)
        signal[rsi < self.oversold] = 1
        signal[rsi > self.overbought] = -1

        return signal

class MACDSignal(SignalBase):
    """Long when MACD histogram > 0 short when < 0"""

    @property 
    def name(self) -> str:
        return "MACD"

    def generate(self, df: pd.DataFrame) -> pd.Series:
        if 'macd_histogram' not in df.columns:
            raise ValueError("DataFrame must contain 'macd_histogram'. Run FeatureEngine with include_ta = True first.")

        hist = df['macd_histogram']
        signal = np.sign(hist)
        signal = signal.replace(0, np.nan).fillna(0).astype(int)

        return signal

class SignalCombiner:
    """Combine multiple signals into a single signal with optional weights."""

    def __init__(self, signals: Dict[str, SignalBase], weights: Optional[Dict[str, float]] = None):
        """
            Args:
                signals: Dictionary of signal name -> SignalBase instance
                weights: Dictionary of signal name -> weight (default None = equal weights)
        """
        self.signals = signals 
        self.weights = weights or {name: 1.0 for name in signals}

    def generate(self, df: pd.DataFrame) -> pd.Series:
        """Generate combined signal from feature DataFrame."""
        results = {}

        for name, signal_gen in self.signals.items():
            sig = signal_gen.generate(df)
            weight = self.weights.get(name, 1.0)
            results[name] = sig * weight

        combined = pd.DataFrame(results).sum(axis=1)
        total_weight = sum(self.weights.get(n, 1.0) for n in self.signals)
        combined = combined / total_weight

        discrete = pd.Series(0, index=df.index)
        discrete[combined > 0.33] = 1
        discrete[combined < -0.33] = -1

        return discrete

def momentum_signal(df: pd.DataFrame, window: int = 21) -> pd.Series:
    """Convenience function for MomentumSignal."""
    return MomentumSignal(window).generate(df)

def rsi_signal(df: pd.DataFrame, oversold: float = 30, overbought: float = 70) -> pd.Series:
    """Convenience function for RSISignal."""
    return RSISignal(oversold, overbought).generate(df)

def macd_signal(df: pd.DataFrame) -> pd.Series:
    """Convenience function for MACDSignal."""
    return MACDSignal().generate(df)