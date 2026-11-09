"""Performance statistics matching the spirit of Antonacci Tables 1, 8, 10."""

from __future__ import annotations

import numpy as np
import pandas as pd

PPY = 12


def _max_drawdown(r: pd.Series) -> float:
    wealth = (1.0 + r).cumprod()
    dd = wealth / wealth.cummax() - 1.0
    return float(dd.min()) if len(dd) else float("nan")


def performance_stats(
    r: pd.Series,
    rf: pd.Series | None = None,
    periods_per_year: int = PPY,
    trades: int | None = None,
) -> dict:
    """Summary stats for a monthly return series.

    * ``cagr`` — geometric annual return.
    * ``vol`` — sample monthly stdev × √12.
    * ``sharpe`` — mean excess / stdev excess × √12 (T-bill as rf when given).
    * ``sharpe_geom`` — (CAGR − rf CAGR) / vol, closer to Antonacci's reported Sharpe.
    * ``kurtosis`` — Pearson kurtosis (normal = 3), matching Table 10.
    """
    r = r.dropna().astype(float)
    out = {
        "n_months": int(len(r)),
        "start": str(r.index.min().date()) if len(r) else None,
        "end": str(r.index.max().date()) if len(r) else None,
        "cagr": float("nan"),
        "vol": float("nan"),
        "sharpe": float("nan"),
        "sharpe_geom": float("nan"),
        "max_dd": float("nan"),
        "pct_positive": float("nan"),
        "skew": float("nan"),
        "kurtosis": float("nan"),
        "mean_monthly": float("nan"),
        "trades_per_year": float("nan"),
        "rf_cagr": float("nan"),
        "wealth_end": float("nan"),
    }
    if len(r) < 2:
        return out
    years = len(r) / periods_per_year
    wealth = float((1.0 + r).prod())
    out["wealth_end"] = wealth
    out["cagr"] = wealth ** (1.0 / years) - 1.0
    out["vol"] = float(r.std(ddof=1) * np.sqrt(periods_per_year))
    out["mean_monthly"] = float(r.mean())
    out["max_dd"] = _max_drawdown(r)
    out["pct_positive"] = float((r > 0).mean())
    out["skew"] = float(r.skew())
    out["kurtosis"] = float(r.kurtosis() + 3.0)  # Pearson
    if rf is not None:
        aligned = rf.reindex(r.index).astype(float)
        if aligned.notna().sum() >= 2:
            ex = (r - aligned).dropna()
            if ex.std(ddof=1) > 0:
                out["sharpe"] = float(ex.mean() / ex.std(ddof=1) * np.sqrt(periods_per_year))
            rf_wealth = float((1.0 + aligned.reindex(r.index).fillna(0.0)).prod())
            out["rf_cagr"] = rf_wealth ** (1.0 / years) - 1.0
            if out["vol"] > 0:
                out["sharpe_geom"] = (out["cagr"] - out["rf_cagr"]) / out["vol"]
    else:
        if r.std(ddof=1) > 0:
            out["sharpe"] = float(r.mean() / r.std(ddof=1) * np.sqrt(periods_per_year))
        if out["vol"] > 0:
            out["sharpe_geom"] = out["cagr"] / out["vol"]
    if trades is not None and years > 0:
        out["trades_per_year"] = trades / years
    return out


def drawdown_series(r: pd.Series) -> pd.Series:
    r = r.dropna()
    wealth = (1.0 + r).cumprod()
    return wealth / wealth.cummax() - 1.0


def wealth_index(r: pd.Series, start: float = 100.0) -> pd.Series:
    r = r.dropna()
    return start * (1.0 + r).cumprod()


def count_switches(holdings: pd.Series) -> int:
    """Number of times the held asset changes after the first valid holding."""
    h = holdings.dropna()
    if len(h) < 2:
        return 0
    return int((h != h.shift(1)).iloc[1:].sum())
