"""Download, cache, and assemble the monthly total-return panel.

Public sources only: Yahoo Finance (adjusted close = total return), FRED (gold
spot, 3-month T-bill yield), Kenneth French research library (monthly T-bill
return). The processed monthly CSV is the series we ship so a third party can
reproduce without network access.
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import requests
import yfinance as yf

from dualmomentum.paths import DATA_PROC, DATA_RAW, ensure_dirs

YAHOO_START = "1970-01-01"
YAHOO_END = "2026-07-05"  # exclusive-ish; keep a few days past 2026-06-30
PANEL_END = pd.Timestamp("2026-06-30")

# Yahoo tickers we actually need, plus fallbacks used only for splicing.
YAHOO_TICKERS = [
    "VFINX",  # US large cap, 1976
    "VGTSX",  # total international, 1996
    "VWEHX",  # high yield, 1978
    "VFICX",  # intermediate IG, 1993
    "VGSIX",  # equity REIT investor
    "VGSLX",  # equity REIT admiral
    "VNQ",  # equity REIT ETF
    "NLY",  # Annaly, mREIT proxy
    "VUSTX",  # long-term Treasury
    "TLT",
    "GLD",
    "GC=F",
    "SPY",
    "VBMFX",  # total bond, 60/40 sleeve
    "BIL",
    "EFA",
    "REM",
]

FRED_TBILL = "TB3MS"
# Public-domain monthly gold USD/oz (World Bank Pink Sheet via datasets/gold-prices).
GOLD_CSV = "https://raw.githubusercontent.com/datasets/gold-prices/master/data/monthly.csv"

# Final panel column → human label and paper analogue.
ASSET_META = {
    "US": {"label": "US equities (VFINX)", "paper": "MSCI US", "module": "equities", "role": "risky"},
    "INTL": {"label": "International equities (VGTSX)", "paper": "EAFE+ / MSCI ACWI ex-US", "module": "equities", "role": "risky"},
    "HY": {"label": "High yield (VWEHX)", "paper": "BofA ML US Cash Pay HY", "module": "credit", "role": "risky"},
    "IG": {"label": "Intermediate IG credit (VFICX)", "paper": "Barclays US Intermediate Credit", "module": "credit", "role": "risky"},
    "EREIT": {"label": "Equity REITs (VGSIX/VGSLX)", "paper": "FTSE NAREIT equity REITs", "module": "reits", "role": "risky"},
    "MREIT": {"label": "Mortgage REIT proxy (NLY)", "paper": "FTSE NAREIT mortgage REITs", "module": "reits", "role": "risky"},
    "GOLD": {"label": "Gold (World Bank Pink Sheet)", "paper": "London PM gold fix", "module": "stress", "role": "risky"},
    "TREAS": {"label": "Long Treasuries (VUSTX)", "paper": "Barclays US Long Treasury", "module": "stress", "role": "risky"},
    "TBILL": {"label": "T-bills (French RF, TB3MS tail)", "paper": "BofA ML 3-month T-bill", "module": "all", "role": "safe"},
    "BOND": {"label": "US aggregate bond (VBMFX)", "paper": "World 60/40 bond sleeve", "module": "bench", "role": "benchmark"},
    "SPY": {"label": "SPY", "paper": "US market ETF check", "module": "bench", "role": "benchmark"},
}

MODULES = {
    "equities": ["US", "INTL"],
    "credit": ["HY", "IG"],
    "reits": ["EREIT", "MREIT"],
    "stress": ["GOLD", "TREAS"],
}
SAFE = "TBILL"
MODULE_ORDER = ["equities", "credit", "reits", "stress"]

FRENCH_URL = "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/F-F_Research_Data_Factors_CSV.zip"
FRED_CSV = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"


def _get(url: str, timeout: int = 60) -> bytes:
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    return r.content


def download_yahoo(force: bool = False) -> dict[str, pd.Series]:
    """Daily total-return index (auto-adjusted close) per ticker."""
    ensure_dirs()
    out: dict[str, pd.Series] = {}
    cache = DATA_RAW / "yahoo_daily.csv"
    if cache.exists() and not force:
        wide = pd.read_csv(cache, index_col=0, parse_dates=True)
        return {c: wide[c].dropna() for c in wide.columns}

    frames = []
    for t in YAHOO_TICKERS:
        df = yf.download(
            t,
            start=YAHOO_START,
            end=YAHOO_END,
            auto_adjust=True,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            print(f"yahoo miss: {t}")
            continue
        close = df["Close"] if "Close" in df.columns else df.iloc[:, 0]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:, 0]
        s = close.copy()
        s.name = t
        s.index = pd.to_datetime(s.index).tz_localize(None)
        frames.append(s)
        print(f"yahoo {t}: {s.dropna().index.min().date()} → {s.dropna().index.max().date()} ({s.dropna().shape[0]})")
    if not frames:
        raise RuntimeError("Yahoo download returned nothing")
    wide = pd.concat(frames, axis=1).sort_index()
    wide.to_csv(cache)
    return {c: wide[c].dropna() for c in wide.columns}


def download_wb_gold(force: bool = False) -> pd.Series:
    """World Bank Pink Sheet monthly average gold price, USD/oz, month-end stamped."""
    ensure_dirs()
    cache = DATA_RAW / "gold_wb_monthly.csv"
    if cache.exists() and not force:
        s = pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = "GOLD"
        return s
    raw = _get(GOLD_CSV)
    df = pd.read_csv(io.BytesIO(raw))
    date_col = df.columns[0]
    px_col = df.columns[1]
    dt = pd.to_datetime(df[date_col], errors="coerce")
    # YYYY-MM stamps as month-start; move to month-end so they join the other series.
    dt = dt.dt.to_period("M").dt.to_timestamp("M")
    s = pd.Series(pd.to_numeric(df[px_col], errors="coerce").values, index=dt, name="GOLD")
    s = s[s.index.notna()].dropna().sort_index()
    s = s[~s.index.duplicated(keep="last")]
    s.to_csv(cache, header=True)
    print(f"WB gold: {s.index.min().date()} → {s.index.max().date()} ({len(s)})")
    return s


def download_fred_series(sid: str) -> pd.Series:
    raw = _get(FRED_CSV.format(sid=sid))
    df = pd.read_csv(io.BytesIO(raw))
    date_col = df.columns[0]
    df[date_col] = pd.to_datetime(df[date_col], errors="coerce")
    val = pd.to_numeric(df[sid] if sid in df.columns else df.iloc[:, 1], errors="coerce")
    s = pd.Series(val.values, index=df[date_col], name=sid)
    s = s[s.index.notna()].sort_index()
    return s.dropna()


def download_french_rf(force: bool = False) -> pd.Series:
    ensure_dirs()
    cache = DATA_RAW / "french_rf_monthly.csv"
    if cache.exists() and not force:
        s = pd.read_csv(cache, index_col=0, parse_dates=True).iloc[:, 0]
        s.name = "RF"
        return s
    zbytes = _get(FRENCH_URL)
    with zipfile.ZipFile(io.BytesIO(zbytes)) as zf:
        name = zf.namelist()[0]
        text = zf.read(name).decode("utf-8", errors="replace")
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(",")]
        if not parts or not parts[0]:
            # blank line starts the annual section
            if rows:
                break
            continue
        key = parts[0]
        if len(key) == 6 and key.isdigit() and len(parts) >= 5:
            # YYYYMM, Mkt-RF, SMB, HML, RF
            try:
                rf = float(parts[4])
            except ValueError:
                continue
            rows.append((key, rf))
    if not rows:
        raise RuntimeError("failed to parse French RF")
    idx = pd.to_datetime([r[0] + "01" for r in rows], format="%Y%m%d") + pd.offsets.MonthEnd(0)
    # French RF is already a monthly *percent*
    s = pd.Series([r[1] / 100.0 for r in rows], index=idx, name="RF")
    s.to_csv(cache, header=True)
    print(f"french RF: {s.index.min().date()} → {s.index.max().date()} ({len(s)})")
    return s


def _month_end(s: pd.Series) -> pd.Series:
    s = s.dropna().sort_index()
    s.index = pd.to_datetime(s.index).tz_localize(None)
    return s.resample("ME").last().dropna()


def _splice_levels(primary: pd.Series, secondary: pd.Series, name: str) -> pd.Series:
    """Continue ``primary`` with ``secondary`` returns after primary ends.

    Levels of ``secondary`` are rescaled to primary's last overlapping (or last)
    value so the series is a continuous total-return index.
    """
    a = _month_end(primary)
    b = _month_end(secondary)
    if a.empty:
        out = b.copy()
        out.name = name
        return out
    extra = b[b.index > a.index.max()]
    if extra.empty:
        a = a.copy()
        a.name = name
        return a
    # scale extra so it continues the last primary level using extra's own growth
    # find last b level at or before a's end for a ratio; if none, use first extra vs last a via returns only
    b_before = b[b.index <= a.index.max()]
    if not b_before.empty and b_before.iloc[-1] != 0:
        scale = a.iloc[-1] / b_before.iloc[-1]
        cont = extra * scale
    else:
        # chain by returns: first extra month return vs previous b, applied to last a
        b_full = pd.concat([b_before, extra]).sort_index()
        rets = b_full.pct_change()
        extra_rets = rets.reindex(extra.index)
        levels = [a.iloc[-1]]
        for rt in extra_rets.fillna(0.0):
            levels.append(levels[-1] * (1.0 + rt))
        cont = pd.Series(levels[1:], index=extra.index)
    out = pd.concat([a, cont]).sort_index()
    out = out[~out.index.duplicated(keep="last")]
    out.name = name
    return out


def _tbill_from_yield(tb3ms: pd.Series) -> pd.Series:
    """Monthly T-bill return from the FRED TB3MS annualized percent yield."""
    y = tb3ms.dropna() / 100.0
    r = (1.0 + y) ** (1.0 / 12.0) - 1.0
    r.name = "TBILL_YLD"
    return r


def build_panel(force: bool = False) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Return (monthly_prices, monthly_returns, manifest). Caches processed CSVs."""
    ensure_dirs()
    prices_path = DATA_PROC / "monthly_prices.csv"
    rets_path = DATA_PROC / "monthly_returns.csv"
    man_path = DATA_PROC / "manifest.json"
    if prices_path.exists() and rets_path.exists() and man_path.exists() and not force:
        prices = pd.read_csv(prices_path, index_col=0, parse_dates=True)
        rets = pd.read_csv(rets_path, index_col=0, parse_dates=True)
        manifest = json.loads(man_path.read_text())
        return prices, rets, manifest

    yahoo = download_yahoo(force=force)
    french_rf = download_french_rf(force=force)
    tb3ms = download_fred_series(FRED_TBILL)
    tb3ms.to_csv(DATA_RAW / "fred_TB3MS.csv", header=True)
    print(f"FRED TB3MS: {tb3ms.index.min().date()} → {tb3ms.index.max().date()}")

    # Gold: World Bank Pink Sheet monthly average (long history). FRED's LBMA
    # daily fix was pulled in 2022. Extend the tail with GLD month-end if needed.
    gold = download_wb_gold(force=force)
    gold_notes = [f"World Bank Pink Sheet monthly gold {gold.index.min().date()}→{gold.index.max().date()}"]
    if "GLD" in yahoo:
        gld_me = _month_end(yahoo["GLD"])
        if gld_me.index.max() > gold.index.max():
            gold = _splice_levels(gold, yahoo["GLD"], "GOLD")
            gold_notes.append(f"spliced GLD month-end through {gld_me.index.max().date()}")
    gold.name = "GOLD"

    def y(ticker: str) -> pd.Series:
        if ticker not in yahoo:
            raise KeyError(ticker)
        return _month_end(yahoo[ticker])

    # Equity REITs: VGSIX (investor) spliced to VGSLX (same portfolio, admiral).
    ereit = y("VGSIX") if "VGSIX" in yahoo else None
    if ereit is None or ereit.index.max() < PANEL_END - pd.offsets.MonthEnd(2):
        if "VGSLX" in yahoo:
            ereit = _splice_levels(ereit if ereit is not None else y("VGSLX"), yahoo["VGSLX"], "EREIT")
        elif "VNQ" in yahoo:
            ereit = _splice_levels(ereit if ereit is not None else y("VNQ"), yahoo["VNQ"], "EREIT")
    ereit.name = "EREIT"

    treas = y("VUSTX")
    if treas.index.max() < PANEL_END - pd.offsets.MonthEnd(2) and "TLT" in yahoo:
        treas = _splice_levels(treas, yahoo["TLT"], "TREAS")
    treas.name = "TREAS"

    # T-bills: French monthly RF (true return) as far as it goes, then TB3MS yield conversion.
    tb_fr = french_rf.copy()
    tb_fr.index = pd.to_datetime(tb_fr.index).to_period("M").to_timestamp("M")
    tb_fr = tb_fr[~tb_fr.index.duplicated(keep="last")].sort_index()
    tb_y = _tbill_from_yield(_month_end(tb3ms))
    tb_y.index = pd.to_datetime(tb_y.index).to_period("M").to_timestamp("M")
    tbill_notes = [f"French RF {tb_fr.index.min().date()}→{tb_fr.index.max().date()}"]
    extra_tb = tb_y[tb_y.index > tb_fr.index.max()]
    if extra_tb.empty:
        tbill_r = tb_fr
    else:
        tbill_r = pd.concat([tb_fr, extra_tb])
        tbill_notes.append(f"TB3MS yield conversion {extra_tb.index.min().date()}→{extra_tb.index.max().date()}")
    tbill_r = tbill_r.sort_index()
    tbill_r = tbill_r[~tbill_r.index.duplicated(keep="last")]
    tbill_r.name = "TBILL"
    # Reconstruct a T-bill total-return index from monthly returns (start at 1.0).
    tbill_px = (1.0 + tbill_r).cumprod()
    tbill_px.name = "TBILL"

    prices = pd.DataFrame(
        {
            "US": y("VFINX"),
            "INTL": y("VGTSX"),
            "HY": y("VWEHX"),
            "IG": y("VFICX"),
            "EREIT": ereit,
            "MREIT": y("NLY"),
            "GOLD": gold,
            "TREAS": treas,
            "TBILL": tbill_px,
            "BOND": y("VBMFX"),
            "SPY": y("SPY") if "SPY" in yahoo else pd.Series(dtype=float),
        }
    )
    prices = prices.sort_index()
    prices = prices.loc[prices.index <= PANEL_END]
    rets = prices.pct_change(fill_method=None)
    # T-bill returns should match the RF series exactly on the French window — overwrite
    # the pct_change of the reconstructed index with the original RF (avoids compounding noise).
    rets["TBILL"] = tbill_r.reindex(rets.index)

    coverage = {}
    for c in prices.columns:
        s = prices[c].dropna()
        coverage[c] = {
            "start": str(s.index.min().date()) if len(s) else None,
            "end": str(s.index.max().date()) if len(s) else None,
            "n": int(len(s)),
        }

    # Common sample for the four modules + T-bill.
    core = ["US", "INTL", "HY", "IG", "EREIT", "MREIT", "GOLD", "TREAS", "TBILL"]
    common = prices[core].dropna().index
    manifest = {
        "built_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "panel_end": str(PANEL_END.date()),
        "yahoo_tickers": YAHOO_TICKERS,
        "gold_construction": gold_notes,
        "tbill_construction": tbill_notes,
        "ereit_end": str(ereit.dropna().index.max().date()),
        "coverage": coverage,
        "common_start": str(common.min().date()) if len(common) else None,
        "common_end": str(common.max().date()) if len(common) else None,
        "common_n": int(len(common)),
        "notes": {
            "MREIT": "NLY (Annaly) is a single-name agency mREIT, not the NAREIT mortgage REIT index.",
            "GOLD": "World Bank Pink Sheet monthly average USD/oz (datasets/gold-prices). Month-average, not LBMA PM fix. Gold pays no dividend.",
            "TBILL": "Kenneth French monthly RF (1-month T-bill return), TB3MS yield conversion only to extend the tail.",
            "INTL": "VGTSX is ACWI ex-US (developed + emerging), slightly broader than EAFE.",
        },
    }
    prices.to_csv(prices_path)
    rets.to_csv(rets_path)
    man_path.write_text(json.dumps(manifest, indent=2))
    print(f"common sample: {manifest['common_start']} → {manifest['common_end']} ({manifest['common_n']} months)")
    return prices, rets, manifest


def load_panel() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    return build_panel(force=False)
