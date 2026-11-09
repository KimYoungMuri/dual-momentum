"""Unit tests: signal lag, skip-a-month, T-bill overlay, 1/N composite."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dualmomentum.backtest import dual_momentum_module, inverse_vol_composite, take_chosen
from dualmomentum.signals import trailing_return


def _months(n: int, start="2000-01-31") -> pd.DatetimeIndex:
    return pd.date_range(start, periods=n, freq="ME")


def test_trailing_12_0_uses_current_month():
    idx = _months(14)
    r = pd.DataFrame({"A": 0.01}, index=idx)
    r.loc[idx[12], "A"] = 1.0  # huge month t=12 (0-based), the 13th month
    m = trailing_return(r, n=12, skip=0)["A"]
    # first valid at idx[11] (12 months 0..11)
    assert pd.isna(m.iloc[10])
    assert np.isfinite(m.iloc[11])
    # month idx[12] must include the +100% return
    assert m.iloc[12] > m.iloc[11]


def test_trailing_12_1_skips_current_month():
    idx = _months(15)
    r = pd.DataFrame({"A": 0.01}, index=idx)
    r.loc[idx[13], "A"] = 1.0
    m0 = trailing_return(r, n=12, skip=0)["A"]
    m1 = trailing_return(r, n=12, skip=1)["A"]
    # 12-1 at idx[13] equals 12-0 at idx[12] (skipped the spike)
    assert abs(m1.iloc[13] - m0.iloc[12]) < 1e-12
    assert m0.iloc[13] > m1.iloc[13]


def test_dual_holds_next_month_not_this_month():
    """A beats B until t, B has a last-month spike: 12-0 switches for t+1, not t."""
    idx = _months(16)
    a = np.full(16, 0.02)
    b = np.full(16, 0.00)
    b[13] = 0.50  # spike in month idx[13]
    r = pd.DataFrame({"A": a, "B": b, "TBILL": 0.001}, index=idx)
    dual = dual_momentum_module(r, ["A", "B"], "TBILL", lookback=12, skip=0, name="d")
    # holdings at idx[14] (next month) should be B; holdings at idx[13] still A
    assert dual.holdings.loc[idx[13]] == "A"
    assert dual.holdings.loc[idx[14]] == "B"
    assert abs(dual.returns.loc[idx[14]] - r.loc[idx[14], "B"]) < 1e-12


def test_absolute_overlay_to_tbills():
    idx = _months(16)
    r = pd.DataFrame(
        {"A": -0.02, "B": -0.03, "TBILL": 0.004},
        index=idx,
    )
    dual = dual_momentum_module(r, ["A", "B"], "TBILL", lookback=12, skip=0)
    # after lookback, everything has lost to T-bills
    h = dual.holdings.dropna()
    assert (h == "TBILL").all()
    assert np.allclose(dual.returns.loc[h.index], r.loc[h.index, "TBILL"])


def test_take_chosen_and_invvol_lag():
    idx = _months(20)
    r = pd.DataFrame(
        {"m1": np.linspace(0.01, 0.02, 20), "m2": np.linspace(0.03, -0.01, 20)},
        index=idx,
    )
    choice = pd.Series(["m1"] * 10 + ["m2"] * 10, index=idx)
    got = take_chosen(r, choice)
    assert abs(got.iloc[0] - r.iloc[0]["m1"]) < 1e-12
    assert abs(got.iloc[-1] - r.iloc[-1]["m2"]) < 1e-12
    ret, w = inverse_vol_composite(r, vol_lookback=5)
    # first weight row that is finite must not use that month's own return
    first = w.dropna(how="any").index[0]
    # w at first equals invvol computed from returns up to previous month
    prev = r.loc[:first].iloc[:-1].tail(5)
    vol = prev.std(ddof=1)
    inv = 1 / vol
    expect = inv / inv.sum()
    assert np.allclose(w.loc[first].to_numpy(), expect.to_numpy(), rtol=1e-10)
