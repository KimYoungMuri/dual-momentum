"""HW5 analysis: Antonacci dual momentum, 1998–2026-06, plus extra credit.

Usage (from hw5/):  python scripts/run_all.py
       with refresh: python scripts/run_all.py --download
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from dualmomentum.backtest import (  # noqa: E402
    absolute_momentum,
    dual_momentum_module,
    equal_weight,
    inverse_vol_composite,
    relative_momentum,
)
from dualmomentum.data import MODULE_ORDER, MODULES, SAFE, build_panel, load_panel  # noqa: E402
from dualmomentum.metrics import count_switches, drawdown_series, performance_stats, wealth_index  # noqa: E402
from dualmomentum.paths import FIG, OUT, TAB, ensure_dirs  # noqa: E402

plt.rcParams.update(
    {
        "mathtext.fontset": "cm",
        "font.family": "serif",
        "font.size": 9,
        "axes.titlesize": 11,
        "axes.labelsize": 9,
        "figure.dpi": 140,
        "savefig.dpi": 160,
        "axes.grid": True,
        "grid.alpha": 0.25,
    }
)

PAPER_TABLE8 = {
    "equities": {"cagr": 0.0949, "vol": 0.0941, "sharpe": 0.39, "max_dd": -0.1498, "pct_positive": 0.81},
    "credit": {"cagr": 0.0762, "vol": 0.0439, "sharpe": 0.45, "max_dd": -0.0782, "pct_positive": 0.79},
    "reits": {"cagr": 0.2214, "vol": 0.1645, "sharpe": 0.90, "max_dd": -0.2374, "pct_positive": 0.77},
    "stress": {"cagr": 0.1327, "vol": 0.1649, "sharpe": 0.43, "max_dd": -0.2478, "pct_positive": 0.63},
}
PAPER_TABLE10 = {
    "equities": {"cagr": 0.1579, "vol": 0.1277, "sharpe": 0.73, "max_dd": -0.2301},
    "credit": {"cagr": 0.1049, "vol": 0.0474, "sharpe": 0.97, "max_dd": -0.0820},
    "reits": {"cagr": 0.1678, "vol": 0.1324, "sharpe": 0.77, "max_dd": -0.2374},
    "stress": {"cagr": 0.1665, "vol": 0.1704, "sharpe": 0.59, "max_dd": -0.2478},
    "composite": {"cagr": 0.1493, "vol": 0.0799, "sharpe": 1.07, "max_dd": -0.1092},
}


def _slice(s: pd.Series, start, end) -> pd.Series:
    out = s.copy()
    if start is not None:
        out = out[out.index >= pd.Timestamp(start)]
    if end is not None:
        out = out[out.index <= pd.Timestamp(end)]
    return out


def _stats(s: pd.Series, rf: pd.Series, start, end, holdings: pd.Series | None = None) -> dict:
    r = _slice(s, start, end).dropna()
    rf_s = rf.reindex(r.index)
    trades = count_switches(_slice(holdings, start, end)) if holdings is not None else None
    st = performance_stats(r, rf_s, trades=trades)
    if len(r):
        st["total_return"] = float((1.0 + r).prod() - 1.0)
    else:
        st["total_return"] = float("nan")
    return st


def _util(holdings: pd.Series, start, end) -> dict:
    h = _slice(holdings, start, end).dropna()
    if h.empty:
        return {}
    vc = h.value_counts(normalize=True)
    return {str(k): float(v) for k, v in vc.items()}


def _save_fig(fig, name: str) -> None:
    fig.tight_layout()
    fig.savefig(FIG / name, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--download", action="store_true", help="refresh raw downloads")
    args = parser.parse_args()
    ensure_dirs()

    prices, rets, manifest = build_panel(force=args.download) if args.download else load_panel()
    core = ["US", "INTL", "HY", "IG", "EREIT", "MREIT", "GOLD", "TREAS", "TBILL"]
    panel = rets[core].dropna(how="any")
    rf = panel["TBILL"]

    # First holding month: need 12 months of history (+1 for the lag).
    # dual_momentum_module already NaNs until then.
    dual = {}
    rel = {}
    dual_skip = {}
    for name, risky in MODULES.items():
        dual[name] = dual_momentum_module(panel, risky, SAFE, lookback=12, skip=0, name=f"{name}_dual")
        rel[name] = relative_momentum(panel, risky, lookback=12, skip=0, name=f"{name}_rel")
        dual_skip[name] = dual_momentum_module(panel, risky, SAFE, lookback=12, skip=1, name=f"{name}_dual_12_1")

    dual_r = pd.DataFrame({k: dual[k].returns for k in MODULE_ORDER})
    rel_r = pd.DataFrame({k: rel[k].returns for k in MODULE_ORDER})
    skip_r = pd.DataFrame({k: dual_skip[k].returns for k in MODULE_ORDER})

    composite = dual_r.mean(axis=1, skipna=False)
    composite.name = "composite_dual"
    composite_rel = rel_r.mean(axis=1, skipna=False)
    composite_rel.name = "composite_relative"
    composite_12_1 = skip_r.mean(axis=1, skipna=False)
    composite_12_1.name = "composite_12_1"

    # Absolute-momentum composite: 1/8 of the eight single-asset TS-momentum sleeves.
    abs_sleeves = {}
    for asset in [a for m in MODULE_ORDER for a in MODULES[m]]:
        abs_sleeves[asset] = absolute_momentum(panel, asset, SAFE, lookback=12, skip=0, name=f"abs_{asset}")
    abs_mod = {}
    for name, risky in MODULES.items():
        abs_mod[name] = pd.DataFrame({a: abs_sleeves[a].returns for a in risky}).mean(axis=1, skipna=False)
    composite_abs = pd.DataFrame(abs_mod).mean(axis=1, skipna=False)
    composite_abs.name = "composite_absolute"

    ew_risky = equal_weight(panel, [a for m in MODULE_ORDER for a in MODULES[m]])
    ew_risky.name = "ew8"
    sixty_forty = 0.6 * panel["US"] + 0.4 * rets["BOND"].reindex(panel.index)
    sixty_forty.name = "sixty_forty"

    invvol_r, invvol_w = inverse_vol_composite(dual_r, vol_lookback=12)
    invvol_r.name = "composite_invvol"
    invvol_12_1, invvol_12_1_w = inverse_vol_composite(skip_r, vol_lookback=12)
    invvol_12_1.name = "composite_12_1_invvol"

    # Align to first date where the paper composite is defined (all 4 modules).
    valid = composite.dropna().index
    start0 = valid.min()
    end0 = min(valid.max(), pd.Timestamp("2026-06-30"))

    windows = {
        "full": (start0, end0),
        "sub_2000_2009": (pd.Timestamp("2000-01-31"), pd.Timestamp("2009-12-31")),
        "overlap_to_2011": (start0, pd.Timestamp("2011-12-31")),
        "oos_2012_2026": (pd.Timestamp("2012-01-31"), end0),
        "oos_2012_2019": (pd.Timestamp("2012-01-31"), pd.Timestamp("2019-12-31")),
        "oos_2020_2026": (pd.Timestamp("2020-01-31"), end0),
        "gfc": (pd.Timestamp("2007-10-31"), pd.Timestamp("2009-03-31")),
        "covid": (pd.Timestamp("2020-02-29"), pd.Timestamp("2020-03-31")),
        "hikes_2022": (pd.Timestamp("2022-01-31"), pd.Timestamp("2022-12-31")),
    }

    strategies = {
        "US": (panel["US"], None),
        "INTL": (panel["INTL"], None),
        "HY": (panel["HY"], None),
        "IG": (panel["IG"], None),
        "EREIT": (panel["EREIT"], None),
        "MREIT": (panel["MREIT"], None),
        "GOLD": (panel["GOLD"], None),
        "TREAS": (panel["TREAS"], None),
        "TBILL": (panel["TBILL"], None),
        "ew8": (ew_risky, None),
        "sixty_forty": (sixty_forty, None),
        "equities_dual": (dual["equities"].returns, dual["equities"].holdings),
        "credit_dual": (dual["credit"].returns, dual["credit"].holdings),
        "reits_dual": (dual["reits"].returns, dual["reits"].holdings),
        "stress_dual": (dual["stress"].returns, dual["stress"].holdings),
        "equities_rel": (rel["equities"].returns, rel["equities"].holdings),
        "credit_rel": (rel["credit"].returns, rel["credit"].holdings),
        "reits_rel": (rel["reits"].returns, rel["reits"].holdings),
        "stress_rel": (rel["stress"].returns, rel["stress"].holdings),
        "composite_dual": (composite, None),
        "composite_relative": (composite_rel, None),
        "composite_absolute": (composite_abs, None),
        "composite_12_1": (composite_12_1, None),
        "composite_invvol": (invvol_r, None),
        "composite_12_1_invvol": (invvol_12_1, None),
        "equities_12_1": (dual_skip["equities"].returns, dual_skip["equities"].holdings),
        "credit_12_1": (dual_skip["credit"].returns, dual_skip["credit"].holdings),
        "reits_12_1": (dual_skip["reits"].returns, dual_skip["reits"].holdings),
        "stress_12_1": (dual_skip["stress"].returns, dual_skip["stress"].holdings),
    }

    perf_rows = []
    perf_nested: dict[str, dict] = {}
    for wname, (ws, we) in windows.items():
        perf_nested[wname] = {}
        for sname, (ser, hol) in strategies.items():
            st = _stats(ser, rf, ws, we, hol)
            st["strategy"] = sname
            st["window"] = wname
            perf_rows.append(st)
            perf_nested[wname][sname] = st

    perf_df = pd.DataFrame(perf_rows)
    perf_df.to_csv(TAB / "performance_by_window.csv", index=False)

    # Wide tables for the two main windows.
    def wide(window: str, names: list[str]) -> pd.DataFrame:
        recs = []
        for n in names:
            st = perf_nested[window][n]
            recs.append(
                {
                    "strategy": n,
                    "start": st["start"],
                    "end": st["end"],
                    "n_months": st["n_months"],
                    "cagr": st["cagr"],
                    "vol": st["vol"],
                    "sharpe": st["sharpe"],
                    "sharpe_geom": st["sharpe_geom"],
                    "max_dd": st["max_dd"],
                    "pct_positive": st["pct_positive"],
                    "skew": st["skew"],
                    "kurtosis": st["kurtosis"],
                    "trades_per_year": st["trades_per_year"],
                    "total_return": st["total_return"],
                }
            )
        return pd.DataFrame(recs)

    module_names = [
        "US", "INTL", "equities_rel", "equities_dual",
        "HY", "IG", "credit_rel", "credit_dual",
        "EREIT", "MREIT", "reits_rel", "reits_dual",
        "GOLD", "TREAS", "stress_rel", "stress_dual",
        "ew8", "sixty_forty", "TBILL",
        "composite_relative", "composite_absolute", "composite_dual",
        "composite_12_1", "composite_invvol", "composite_12_1_invvol",
    ]
    for w in ["full", "sub_2000_2009", "overlap_to_2011", "oos_2012_2026"]:
        wide(w, module_names).to_csv(TAB / f"performance_{w}.csv", index=False)

    # Utilization.
    util_rows = []
    util_nested: dict[str, dict] = {}
    for wname, (ws, we) in windows.items():
        util_nested[wname] = {}
        for m in MODULE_ORDER:
            u = _util(dual[m].holdings, ws, we)
            util_nested[wname][m] = u
            for asset, p in u.items():
                util_rows.append({"window": wname, "module": m, "asset": asset, "pct": p})
    pd.DataFrame(util_rows).to_csv(TAB / "utilization.csv", index=False)

    # Simultaneous T-bill occupancy of the composite (paper footnote 8 analogue).
    hold_df = pd.DataFrame({m: dual[m].holdings for m in MODULE_ORDER}).loc[valid]
    n_cash = (hold_df == "TBILL").sum(axis=1)
    cash_occ = {f"modules_in_tbill_{k}": float((n_cash == k).mean()) for k in range(5)}

    # Paper Table 8 comparison (2000–2009).
    t8_rows = []
    for m, paper in PAPER_TABLE8.items():
        st = perf_nested["sub_2000_2009"][f"{m}_dual"]
        t8_rows.append(
            {
                "module": m,
                "paper_cagr": paper["cagr"],
                "ours_cagr": st["cagr"],
                "delta_cagr": st["cagr"] - paper["cagr"],
                "paper_vol": paper["vol"],
                "ours_vol": st["vol"],
                "paper_sharpe": paper["sharpe"],
                "ours_sharpe_geom": st["sharpe_geom"],
                "ours_sharpe": st["sharpe"],
                "paper_max_dd": paper["max_dd"],
                "ours_max_dd": st["max_dd"],
                "paper_pct_pos": paper["pct_positive"],
                "ours_pct_pos": st["pct_positive"],
            }
        )
    pd.DataFrame(t8_rows).to_csv(TAB / "paper_table8_comparison.csv", index=False)

    # Monthly ledgers.
    strat_monthly = pd.DataFrame(
        {
            "US": panel["US"],
            "INTL": panel["INTL"],
            "HY": panel["HY"],
            "IG": panel["IG"],
            "EREIT": panel["EREIT"],
            "MREIT": panel["MREIT"],
            "GOLD": panel["GOLD"],
            "TREAS": panel["TREAS"],
            "TBILL": panel["TBILL"],
            "equities_dual": dual["equities"].returns,
            "credit_dual": dual["credit"].returns,
            "reits_dual": dual["reits"].returns,
            "stress_dual": dual["stress"].returns,
            "composite_dual": composite,
            "composite_relative": composite_rel,
            "composite_absolute": composite_abs,
            "composite_12_1": composite_12_1,
            "composite_invvol": invvol_r,
            "composite_12_1_invvol": invvol_12_1,
            "ew8": ew_risky,
            "sixty_forty": sixty_forty,
        }
    )
    strat_monthly.to_csv(TAB / "monthly_strategy_returns.csv")
    hold_df.to_csv(TAB / "monthly_holdings.csv")
    invvol_w.to_csv(TAB / "invvol_weights.csv")

    # Rolling 36-month Sharpe of the composite.
    ex = (composite - rf).dropna()
    roll = ex.rolling(36, min_periods=36)
    roll_sharpe = (roll.mean() / roll.std(ddof=1) * np.sqrt(12)).dropna()
    roll_sharpe.to_csv(TAB / "rolling_36m_sharpe.csv", header=["sharpe"])

    # ------------------------------------------------------------------ figures
    # 1. Growth of $100, full sample.
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    series_plot = {
        "Dual composite": composite,
        "Relative-only composite": composite_rel,
        "1/8 risky (no momentum)": ew_risky,
        "60/40 US/bond": sixty_forty,
        "US equities (VFINX)": panel["US"],
        "T-bills": panel["TBILL"],
    }
    for lab, ser in series_plot.items():
        w = wealth_index(_slice(ser, start0, end0))
        ax.plot(w.index, w.values, label=lab, lw=1.5 if "Dual" in lab else 1.1)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $100 (log)")
    ax.set_title("Composite dual momentum vs benchmarks")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    _save_fig(fig, "growth_full.png")

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    oos_s, oos_e = windows["oos_2012_2026"]
    for lab, ser in series_plot.items():
        w = wealth_index(_slice(ser, oos_s, oos_e))
        ax.plot(w.index, w.values, label=lab, lw=1.5 if "Dual" in lab else 1.1)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $100 (log)")
    ax.set_title("Out of sample: January 2012 – June 2026")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    _save_fig(fig, "growth_oos.png")

    fig, ax = plt.subplots(figsize=(7.6, 4.2))
    for lab, m in [("Equities", "equities"), ("Credit", "credit"), ("REITs", "reits"), ("Stress", "stress")]:
        w = wealth_index(_slice(dual[m].returns, start0, end0))
        ax.plot(w.index, w.values, label=lab, lw=1.2)
    w = wealth_index(_slice(composite, start0, end0))
    ax.plot(w.index, w.values, label="Composite", color="black", lw=1.8)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $100 (log)")
    ax.set_title("Four dual-momentum modules and the 1/N composite")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    _save_fig(fig, "growth_modules.png")

    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    dd = drawdown_series(_slice(composite, start0, end0))
    ax.fill_between(dd.index, dd.values, 0, color="firebrick", alpha=0.55, lw=0)
    ax.plot(dd.index, dd.values, color="firebrick", lw=0.6)
    ax.set_ylabel("Drawdown")
    ax.set_title("Composite dual momentum, month-end drawdown")
    _save_fig(fig, "drawdown_composite.png")

    # Extra credit horse race.
    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    extra = {
        "Dual 12-0, 1/N (paper)": composite,
        "Dual 12-1, 1/N": composite_12_1,
        "Dual 12-0, inv. vol": invvol_r,
        "Dual 12-1, inv. vol": invvol_12_1,
        "Relative only, 1/N": composite_rel,
    }
    for lab, ser in extra.items():
        w = wealth_index(_slice(ser, oos_s, oos_e))
        ax.plot(w.index, w.values, label=lab, lw=1.4)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $100 (log)")
    ax.set_title("Extra credit, OOS 2012–2026 H1")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    _save_fig(fig, "extra_credit_oos.png")

    fig, ax = plt.subplots(figsize=(7.6, 4.4))
    for lab, ser in extra.items():
        w = wealth_index(_slice(ser, start0, end0))
        ax.plot(w.index, w.values, label=lab, lw=1.4)
    ax.set_yscale("log")
    ax.set_ylabel("Growth of $100 (log)")
    ax.set_title("Extra credit, full sample")
    ax.legend(loc="upper left", frameon=False, fontsize=8)
    _save_fig(fig, "extra_credit_full.png")

    # Holdings heatmap.
    color_map = {
        "US": "#1f77b4",
        "INTL": "#5fa8d3",
        "HY": "#d62728",
        "IG": "#f4a261",
        "EREIT": "#2a9d8f",
        "MREIT": "#8ab17d",
        "GOLD": "#e9c46a",
        "TREAS": "#6d597a",
        "TBILL": "#9d9d9d",
    }
    fig, axes = plt.subplots(4, 1, figsize=(7.8, 5.6), sharex=True)
    for ax, m in zip(axes, MODULE_ORDER):
        h = dual[m].holdings.loc[start0:end0]
        codes = sorted(h.dropna().unique(), key=lambda x: (x == "TBILL", x))
        for i, asset in enumerate(codes):
            flag = (h == asset).astype(float)
            ax.fill_between(h.index, i, i + 1, where=flag.reindex(h.index).fillna(0).astype(bool),
                            color=color_map.get(asset, "black"), alpha=0.9, lw=0, label=asset)
        ax.set_yticks([0.5 + i for i in range(len(codes))])
        ax.set_yticklabels(codes, fontsize=8)
        ax.set_ylim(0, len(codes))
        ax.set_ylabel(m, fontsize=8)
        ax.grid(False)
        if ax is axes[0]:
            ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=7)
    axes[0].set_title("Month-end holdings by module (dual 12-0)")
    _save_fig(fig, "holdings.png")

    # Utilization bars, full sample.
    fig, ax = plt.subplots(figsize=(7.4, 3.8))
    assets_order = ["US", "INTL", "HY", "IG", "EREIT", "MREIT", "GOLD", "TREAS", "TBILL"]
    x = np.arange(len(MODULE_ORDER))
    width = 0.22
    # three bars per module: risky A, risky B, tbill — but modules have different names.
    # grouped: for each module, plot its utilization dict.
    bottoms = np.zeros(len(MODULE_ORDER))
    legend_done = set()
    stacked_assets_per_mod = []
    for mi, m in enumerate(MODULE_ORDER):
        stacked_assets_per_mod.append(list(MODULES[m]) + ["TBILL"])
    # Use a common stacked order: risky0, risky1, TBILL
    for layer in range(3):
        heights = []
        colors = []
        labels = []
        for m in MODULE_ORDER:
            assets = list(MODULES[m]) + ["TBILL"]
            a = assets[layer]
            heights.append(util_nested["full"][m].get(a, 0.0))
            colors.append(color_map.get(a, "black"))
            labels.append(a)
        bars = ax.bar(x, heights, 0.55, bottom=bottoms, color=colors, edgecolor="white", lw=0.4)
        for mi, a in enumerate(labels):
            if a not in legend_done and heights[mi] > 0:
                bars[mi].set_label(a)
                legend_done.add(a)
        bottoms = bottoms + np.array(heights)
    ax.set_xticks(x)
    ax.set_xticklabels(["Equities", "Credit", "REITs", "Stress"])
    ax.set_ylim(0, 1)
    ax.set_ylabel("Fraction of months held")
    ax.set_title("Asset utilization, full sample (dual 12-0)")
    ax.legend(loc="upper right", ncol=3, frameon=False, fontsize=7)
    _save_fig(fig, "utilization.png")

    fig, ax = plt.subplots(figsize=(7.6, 3.6))
    ax.plot(roll_sharpe.index, roll_sharpe.values, color="navy", lw=1.2)
    ax.axhline(0, color="black", lw=0.6)
    ax.axhline(float(roll_sharpe.mean()), color="navy", lw=0.8, ls="--",
               label=f"mean {float(roll_sharpe.mean()):.3f}")
    ax.set_ylabel("36-month Sharpe")
    ax.set_title("Composite dual momentum, rolling 36-month Sharpe vs T-bills")
    ax.legend(frameon=False, fontsize=8)
    _save_fig(fig, "rolling_sharpe.png")

    # Episode bars.
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    episodes = ["gfc", "covid", "hikes_2022"]
    labs = ["GFC Oct07–Mar09", "COVID Feb–Mar20", "2022 hiking cycle"]
    names = ["composite_dual", "composite_relative", "ew8", "sixty_forty", "US"]
    pretty = ["Dual", "Relative", "EW8", "60/40", "US"]
    x = np.arange(len(episodes))
    width = 0.15
    for i, (n, p) in enumerate(zip(names, pretty)):
        vals = [perf_nested[e][n]["total_return"] for e in episodes]
        ax.bar(x + (i - 2) * width, vals, width, label=p)
    ax.axhline(0, color="black", lw=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(labs)
    ax.set_ylabel("Total return")
    ax.set_title("Crisis windows")
    ax.legend(frameon=False, fontsize=8, ncol=5, loc="upper right")
    _save_fig(fig, "episodes.png")

    # Inverse-vol weights over time.
    fig, ax = plt.subplots(figsize=(7.6, 3.8))
    ww = invvol_w.dropna(how="any").loc[start0:end0]
    ax.stackplot(ww.index, *[ww[c] for c in MODULE_ORDER],
                 labels=["Equities", "Credit", "REITs", "Stress"], alpha=0.9)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Weight")
    ax.set_title("Inverse-vol module weights (12-month realized vol, lagged)")
    ax.legend(loc="upper left", ncol=4, frameon=False, fontsize=8)
    _save_fig(fig, "invvol_weights.png")

    # ------------------------------------------------------------------ JSON
    def f(x):
        if x is None or (isinstance(x, float) and not np.isfinite(x)):
            return None
        if isinstance(x, (np.floating, float)):
            return float(x)
        if isinstance(x, (np.integer, int)):
            return int(x)
        return x

    def clean(d):
        if isinstance(d, dict):
            return {k: clean(v) for k, v in d.items()}
        if isinstance(d, list):
            return [clean(v) for v in d]
        return f(d)

    results = {
        "manifest": manifest,
        "sample": {
            "first_holding": str(start0.date()),
            "last_holding": str(end0.date()),
            "n_months": int(len(composite.loc[start0:end0].dropna())),
        },
        "windows": {k: {"start": str(pd.Timestamp(a).date()), "end": str(pd.Timestamp(b).date())}
                    for k, (a, b) in windows.items()},
        "performance": clean(perf_nested),
        "utilization": clean(util_nested),
        "cash_occupancy_full": clean(cash_occ),
        "paper_table8": t8_rows,
        "paper_table10": PAPER_TABLE10,
        "invvol_mean_weights": {c: float(invvol_w[c].dropna().mean()) for c in MODULE_ORDER},
    }
    (OUT / "results.json").write_text(json.dumps(results, indent=2, default=str))
    print(f"full sample {start0.date()} → {end0.date()}")
    cd = perf_nested["full"]["composite_dual"]
    print(f"composite dual CAGR={cd['cagr']:.5f} vol={cd['vol']:.5f} Sharpe={cd['sharpe']:.5f} DD={cd['max_dd']:.5f}")
    oos = perf_nested["oos_2012_2026"]["composite_dual"]
    print(f"OOS CAGR={oos['cagr']:.5f} vol={oos['vol']:.5f} Sharpe={oos['sharpe']:.5f} DD={oos['max_dd']:.5f}")
    print(f"wrote {OUT / 'results.json'}")


if __name__ == "__main__":
    main()
