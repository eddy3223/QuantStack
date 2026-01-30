import pandas as pd

def check_gross_exposure(
    positions: pd.DataFrame,
    target: float, 
    tolerance: float = 0.05,
) -> pd.Series: 
    gross = positions.abs().sum(axis=1)
    deviation = gross / target - 1.0
    return deviation.abs() < tolerance