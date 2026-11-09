"""Momentum lookbacks. All operations are month-end, no intra-month peeking."""

from __future__ import annotations

import numpy as np
import pandas as pd


def trailing_return(monthly_returns: pd.DataFrame | pd.Series, n: int = 12, skip: int = 0) -> pd.DataFrame | pd.Series:
    """Compounded return over ``n`` months, optionally skipping the most recent ``skip`` months.

    At month-end ``t`` (after ``R_t`` is known):

    * ``skip=0, n=12`` (paper 12-0): product of ``R_{t-11}, ..., R_t``.
    * ``skip=1, n=12`` (12-1): product of ``R_{t-12}, ..., R_{t-1}`` — skips last-month reversal.

    The value at ``t`` uses only returns dated ``t`` or earlier. It is a signal for month ``t+1``.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if skip < 0:
        raise ValueError("skip must be >= 0")
    log = np.log1p(monthly_returns)
    rolled = log.rolling(window=n, min_periods=n).sum()
    if skip:
        rolled = rolled.shift(skip)
    return np.expm1(rolled)
