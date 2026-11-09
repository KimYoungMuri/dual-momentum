# HW5 – Dual Momentum (Antonacci 2013), updated through 2026-06-30

Young Kim (yk3057), Systematic Investment Strategies, Fall 2026.

**Report:** `report/hw5_report.pdf`

Update of Gary Antonacci, *Risk Premia Harvesting Through Dual Momentum* (2013). Four modules
(equities, credit, REITs, economic stress), 12-month dual momentum, equal 25% weights, monthly
rebalance, sample November 1998 – June 2026. Extra credit: skip-a-month (12-1) lookback and
inverse-vol module weights.

## Reproduce

Python 3.12, from `hw5/`:

```bash
python3.12 -m venv .venv && .venv/bin/pip install -r requirements.txt
MPLCONFIGDIR=.mplcache .venv/bin/python -m pytest tests/ -q
MPLCONFIGDIR=.mplcache .venv/bin/python scripts/run_all.py        # uses cached data/processed/
MPLCONFIGDIR=.mplcache .venv/bin/python scripts/build_report.py   # -> report/hw5_report.pdf
```

Network is required only to refresh downloads:

```bash
MPLCONFIGDIR=.mplcache .venv/bin/python scripts/run_all.py --download
```

## Layout

| Path | Content |
|---|---|
| `docs/antonacci_2013_dual_momentum.pdf` | The paper |
| `docs/assignment_page*.png` | Assignment text |
| `data/processed/monthly_returns.csv` | Shipped monthly panel (enough to reproduce) |
| `data/processed/monthly_prices.csv` | Month-end total-return indices |
| `src/dualmomentum/` | Signals, backtest, metrics, data |
| `scripts/run_all.py` | Analysis → `outputs/` |
| `scripts/build_report.py` | PDF write-up |
| `tests/test_lookahead.py` | No look-ahead, skip-month, T-bill overlay |
| `PLAN.md` | Working plan |

## Headline (see the PDF)

- Full sample dual composite: 9.01638% CAGR, 7.44579% vol, Sharpe 0.93231, max DD −14.98158%.
- 2000–09 modules sit next to Antonacci Table 8 (REITs 21.47342% vs paper 22.14000%).
- OOS 2012–2026: dual 6.99688% vs US 15.01906% vs 60/40 9.81373%. Absolute momentum still
  cut the GFC to −0.91400% vs US −45.82052%.
- Extra credit: 12-1 lookback raises OOS CAGR to 9.00196% and Sharpe to 0.97598. Inverse-vol
  module weights do not help.
