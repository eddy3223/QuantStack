import pytest

def test_gross_exposure_is_target(backtest_results):
    positions = backtest_results["positions"]
    gross = positions.abs().sum(axis=1)

    assert gross.mean() == pytest.approx(1.0, rel=0.05)

def test_pnl_is_lagged(backtest_results):
    pnl = backtest_results["pnl"]
    # --- first day must have zero PNL because positions are lagged
    assert pnl.iloc[0].abs().sum() == 0.0

def test_no_nans_in_positions(backtest_results):
    positions = backtest_results["positions"]
    assert not positions.isna().any().any()