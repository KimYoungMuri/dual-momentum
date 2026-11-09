"""Dual-momentum modules, composites, and extra-credit weightings.

Timing convention (enforced everywhere):
    Signal at month-end t uses returns known at t.
    Position is held during month t+1 and earns R_{t+1}.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from dualmomentum.signals import trailing_return


def take_chosen(returns: pd.DataFrame, choice: pd.Series) -> pd.Series:
    """Look up ``returns[t, choice[t]]``. ``choice[t]`` is the asset held during month t."""
    out = np.full(len(returns), np.nan, dtype=float)
    cols = {c: i for i, c in enumerate(returns.columns)}
    vals = returns.to_numpy(dtype=float)
    names = choice.reindex(returns.index).to_numpy()
    for i, a in enumerate(names):
        if isinstance(a, str) and a in cols and np.isfinite(vals[i, cols[a]]):
            out[i] = vals[i, cols[a]]
    return pd.Series(out, index=returns.index, name="return")


def _winner(mom: pd.DataFrame, risky: list[str]) -> pd.Series:
    sub = mom[risky]
    valid = sub.notna().all(axis=1)
    w = pd.Series(index=sub.index, dtype=object)
    if valid.any():
        w.loc[valid] = sub.loc[valid].idxmax(axis=1)
    return w


@dataclass
class ModuleResult:
    name: str
    returns: pd.Series
    holdings: pd.Series
    relative_winner: pd.Series
    in_risky: pd.Series
    momentum: pd.DataFrame
    skip: int = 0
    extras: dict = field(default_factory=dict)


def dual_momentum_module(
    returns: pd.DataFrame,
    risky: list[str],
    safe: str,
    lookback: int = 12,
    skip: int = 0,
    name: str = "",
) -> ModuleResult:
    """Relative winner, then T-bill hurdle. Position for t+1 is set at t."""
    cols = list(dict.fromkeys(list(risky) + [safe]))
    r = returns[cols].astype(float)
    mom = trailing_return(r, n=lookback, skip=skip)
    winner = _winner(mom, risky)
    winner_m = pd.Series(np.nan, index=r.index, dtype=float)
    for dt, a in winner.dropna().items():
        winner_m.loc[dt] = mom.loc[dt, a]
    hurdle = mom[safe]
    in_risky = winner_m > hurdle
    choice_at_t = winner.where(in_risky, safe)
    choice_at_t = choice_at_t.where(winner.notna() & hurdle.notna())
    holdings = choice_at_t.shift(1)  # held during t = decided at t-1
    strat = take_chosen(r, holdings)
    strat.name = name or "dual"
    return ModuleResult(
        name=strat.name,
        returns=strat,
        holdings=holdings,
        relative_winner=winner.shift(1),
        in_risky=in_risky.shift(1),
        momentum=mom,
        skip=skip,
    )


def relative_momentum(
    returns: pd.DataFrame,
    risky: list[str],
    lookback: int = 12,
    skip: int = 0,
    name: str = "",
) -> ModuleResult:
    """Always hold the trailing-return winner. No T-bill overlay."""
    r = returns[risky].astype(float)
    mom = trailing_return(r, n=lookback, skip=skip)
    winner = _winner(mom, risky)
    holdings = winner.shift(1)
    strat = take_chosen(r, holdings)
    strat.name = name or "relative"
    return ModuleResult(
        name=strat.name,
        returns=strat,
        holdings=holdings,
        relative_winner=winner.shift(1),
        in_risky=holdings.notna(),
        momentum=mom,
        skip=skip,
    )


def absolute_momentum(
    returns: pd.DataFrame,
    asset: str,
    safe: str,
    lookback: int = 12,
    skip: int = 0,
    name: str = "",
) -> ModuleResult:
    """Single-asset time-series momentum vs T-bills."""
    r = returns[[asset, safe]].astype(float)
    mom = trailing_return(r, n=lookback, skip=skip)
    in_risky = mom[asset] > mom[safe]
    choice = pd.Series(np.where(in_risky, asset, safe), index=r.index)
    choice = choice.where(mom[asset].notna() & mom[safe].notna())
    holdings = choice.shift(1)
    strat = take_chosen(r, holdings)
    strat.name = name or f"abs_{asset}"
    return ModuleResult(
        name=strat.name,
        returns=strat,
        holdings=holdings,
        relative_winner=pd.Series(asset, index=r.index).where(choice.notna()).shift(1),
        in_risky=in_risky.shift(1),
        momentum=mom,
        skip=skip,
    )


def equal_weight(returns: pd.DataFrame, assets: list[str]) -> pd.Series:
    r = returns[assets].astype(float)
    return r.mean(axis=1, skipna=False)


def inverse_vol_composite(
    module_returns: pd.DataFrame,
    vol_lookback: int = 12,
    min_weight: float | None = None,
    max_weight: float | None = None,
) -> tuple[pd.Series, pd.DataFrame]:
    """Trailing realized-vol weights across modules, lagged one month.

    Weight for month t uses module returns through t-1 only.
    """
    vol = module_returns.rolling(window=vol_lookback, min_periods=vol_lookback).std(ddof=1)
    inv = 1.0 / vol.replace(0.0, np.nan)
    w_at_t = inv.div(inv.sum(axis=1), axis=0)  # known at t, after R_t

    if min_weight is not None or max_weight is not None:
        lo = 0.0 if min_weight is None else min_weight
        hi = 1.0 if max_weight is None else max_weight
        clipped = w_at_t.clip(lower=lo, upper=hi)
        w_at_t = clipped.div(clipped.sum(axis=1), axis=0)

    w_held = w_at_t.shift(1)
    ret = (w_held * module_returns).sum(axis=1, skipna=False)
    # require a full weight vector
    ret = ret.where(w_held.notna().all(axis=1))
    ret.name = "invvol"
    return ret, w_held
