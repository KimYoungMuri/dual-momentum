# HW5 plan — Antonacci Dual Momentum, updated through 2026-06-30

Systematic Investment Strategies, Fall 2026.
Paper: Gary Antonacci, *Risk Premia Harvesting Through Dual Momentum* (Jan 28, 2013). Local copy: `docs/antonacci_2013_dual_momentum.pdf`.

This file is the working plan. Implementation starts after the open decisions at the bottom are confirmed.

---

## What the assignment actually asks

Update Antonacci’s empirical results (paper sample ends Dec 2011) through **2026-06-30**. Four parts:

| Part | Deliverable |
|---|---|
| **(a) Data** | Collect monthly end-of-month series. Must start **before 2011** (overlap with the paper). Ideally covers **2007–2009**. If history reaches 2007, also report the paper’s **1/00–12/09** subsample. Four modules, each with **≥2 risky assets** (different views of that risk) **+ 1 non-risky safe haven**. Describe sources, cleaning, and why each series was chosen. |
| **(b) Implementation** | Self-contained code **and** the collected data. Independent third party can rerun and reproduce. Same momentum criterion as the paper. Same 4-module allocation as the paper. **Do not** run the Section 12 factor-model alphas. |
| **(c) Discussion** | Detailed, critical comparison of our findings vs the paper’s results (Tables 1, 4, 6, 7, 8, 10–12 are the relevant ones; skip Table 18). |
| **(d) Extra credit** | Propose **and show** an improvement to how momentum is used in the construction. |

Course write-up rules we will follow (same as HW4):

- First-page **summary of all answers**, numbers to **≥5 decimals** where they are not whole percents.
- Explain every step; print row/column headers; no unexplained spreadsheet dumps.
- PDF write-up, not a numbers-only workbook.

---

## What the paper actually does (the rules we will copy)

### Dual momentum, per module, each month-end

1. **Relative momentum.** Among the module’s risky assets, pick the one with the highest trailing **12-month total return**.
2. **Absolute momentum.** If that winner also beat **3-month T-bills** over the same 12 months, hold the winner for the **next** month. Otherwise hold T-bills.
3. Repeat independently in each module.
4. **Composite** = equal 25% / 25% / 25% / 25% across the four modules, rebalanced monthly. (Paper cites DeMiguel, Garlappi, Uppal 2009 as the reason not to optimize weights.)

Paper’s own wording (p. 4): *“we adjust all our positions monthly **without skipping a month**.”* Equity-momentum papers usually skip month *t* to avoid short-term reversal. Antonacci does **not**, because the universe mixes gold, bonds, and REITs. See open decision #1.

No transaction costs. Paper turnover is low (~1.2–1.6 switches/year per module).

### Paper modules and indices (1974–2011)

| Module | Risky A | Risky B | Safe haven |
|---|---|---|---|
| Equities | MSCI US | EAFE+ (MSCI EAFE through 1987, MSCI ACWI ex-US after) | BofA ML 3-month T-bill |
| Credit | BofA ML US Cash Pay High Yield (Steele HY mutual-fund avg before Nov 1984) | Barclays US Intermediate Credit | same T-bill |
| Real estate | FTSE NAREIT equity REITs | FTSE NAREIT mortgage REITs | same T-bill |
| Economic stress | London PM gold fix (World Gold Council) | Barclays US Long Treasury | same T-bill |

### Paper headline numbers we will try to get in the ballpark on the overlap window

**Full paper sample, 1974–2011 (Table 10):**

| Series | Ann. return | Ann. vol | Sharpe | Max DD |
|---|---:|---:|---:|---:|
| Equities module | 15.79 | 12.77 | 0.73 | −23.01 |
| Credit module | 10.49 | 4.74 | 0.97 | −8.20 |
| REIT module | 16.78 | 13.24 | 0.77 | −23.74 |
| Stress module | 16.65 | 17.04 | 0.59 | −24.78 |
| **Composite** | **14.93** | **7.99** | **1.07** | **−10.92** |

**1/00–12/09 subsample (Table 8)** — the one the assignment flags if our data reaches 2007:

| Module | Ann. return | Ann. vol | Sharpe | Max DD |
|---|---:|---:|---:|---:|
| Equities | 9.49 | 9.41 | 0.39 | −14.98 |
| Credit | 7.62 | 4.39 | 0.45 | −7.82 |
| REIT | 22.14 | 16.45 | 0.90 | −23.74 |
| Stress | 13.27 | 16.49 | 0.43 | −24.78 |

We will **not** match these exactly: different underlying series (ETFs/mutual funds vs the paper’s institutional indices), expense ratios, and a later start date. The point of (c) is to say what matched, what did not, and why.

---

## Proposed data (public, total-return, long enough for 2007–2009)

Goal: one common monthly panel from ~1997 through **2026-06-30**, so we can (i) overlap the paper through 2011, (ii) report 1/00–12/09, (iii) isolate true OOS 2012–2026 H1.

Yahoo Finance adjusted close (dividends reinvested) + FRED. Mutual funds beat ETFs on history. We will **cache the monthly panel in `data/processed/`** so the submission is reproducible even if Yahoo is down.

| Module | Risky A (paper analogue) | Risky B | Safe haven | Why this pair |
|---|---|---|---|---|
| Equities | `VFINX` Vanguard 500 (1976) → paper MSCI US | `VGTSX` Vanguard Total Intl (1996) → paper EAFE+ / ACWI ex-US | FRED `TB3MS` 3m T-bill, converted to a monthly return | Same two views: US vs rest-of-world. VGTSX includes EM after 1996, slightly broader than EAFE, closer to the paper’s post-1987 EAFE+. |
| Credit | `VWEHX` Vanguard HY (1978) → paper HY | `VFICX` Vanguard Interm-Term IG (1993) → paper intermediate credit | same T-bill | Duration-matched credit vs HY, which is the paper’s point (Table 3). `LQD` is a fallback but starts 2002 and is longer duration. |
| Real estate | `VGSIX` Vanguard REIT (1996) / `VNQ` → paper equity REITs | `NLY` Annaly (1997) as mREIT proxy until/alongside `REM` (2011) | same T-bill | **Weakest mapping.** Paper uses the NAREIT mortgage-REIT *index*. `REM` starts May 2011, so it misses the GFC. NLY is the largest mREIT and is available through 2007–09; we will disclose single-name idiosyncratic risk. |
| Economic stress | FRED gold London PM (`GOLDPMGBD228NLBM` or successor) / `GLD` | `VUSTX` Vanguard Long-Term Treasury (1986) / `TLT` | same T-bill | Same two safe-haven views: flight-to-uncertainty vs flight-to-quality. Gold is a spot price (paper does the same). |

**T-bill conversion.** FRED `TB3MS` is an annualized percent discount/yield. Monthly T-bill return ≈ `(1 + y/100)^(1/12) − 1`. Same series in every module, as the assignment allows.

**Cleaning.** Month-end last available close; total returns from adjusted close; gold as percent change in the PM fix; drop months where any module’s required series is missing (or, if only one asset in a module is missing, delay that module’s start — we prefer a common start). No interpolation of prices. Document every splice (mutual fund → ETF is *not* required if the mutual fund still exists through 2026-06).

**Common sample (expected):** prices from mid-1997 (NLY) ⇒ 12-month lookback ⇒ first holding month **mid/late 1998** through **2026-06**. That covers GFC, the 1/00–12/09 table, paper overlap through 2011, and 14.5 years of true OOS.

---

## Signal timing (no look-ahead)

At month-end \(t\), using month-end total-return indices \(P\):

\[
m_{i,t} = \frac{P_{i,t}}{P_{i,t-12}} - 1
\qquad\text{(or \(P_{i,t-1}/P_{i,t-13}-1\) if we skip last month)}
\]

- Relative winner in module \(k\): \(\arg\max_i m_{i,t}\).
- Hold winner during month \(t+1\) iff \(m_{\text{winner},t} > m_{\text{Tbill},t}\); else hold T-bills during \(t+1\).
- Composite return in \(t+1\) is the equal-weight average of the four module returns.

This is the standard “signal at \(t\), earn \(t+1\)” lag. We will unit-test it on a 3-asset toy series.

---

## Sample windows we will report

| Window | Why |
|---|---|
| Full sample (first holding month → 2026-06) | Headline update |
| 2000-01 → 2009-12 | Direct vs Table 8 (assignment’s requested subsample) |
| Start → 2011-12 | Overlap with the paper’s full sample (different start date, so levels will differ) |
| **2012-01 → 2026-06** | True out-of-sample update — the point of the homework |
| 2007-10 → 2009-03 | GFC stress check (paper Figure 1 narrative) |
| 2020-02 → 2020-03 and 2022 | COVID / inflation-hike regimes the paper never saw |

---

## Metrics and figures (match the paper, then add OOS)

Per asset, per module, and for the composite:

- CAGR (paper’s “Annual Return”), annualized vol, Sharpe vs T-bills, max month-end drawdown, % profit months, trades/year, skew, kurtosis (Table 10).
- Asset utilization % (Table 11 analogue).
- Dual vs relative-only vs buy-and-hold constituents (Tables 1, 4, 6, 7).
- Dual vs utilization-weighted static benchmark (Tables 11–12).
- Composite vs SPY / 60-40 (paper Figures 7, 13).

Figures: growth of $100 (log), underwater drawdown, rolling 36-month Sharpe, module holdings heatmap over time, utilization bars.

**Not doing:** Section 12 six-factor alphas (assignment says skip).

Numbers in the write-up: ≥5 decimal places on rates that are not already whole percents (CAGR 0.12473, Sharpe 0.38721, etc.).

---

## Extra credit (d) — one improvement, shown, not a laundry list

**Primary proposal: skip-last-month 12-1 momentum**, optionally combined with **inverse-vol module weights**.

Why this is a real improvement rather than a tweak:

- The assignment’s wording (“return of last 12 months *(without last-month reversal effects)*”) is closer to 12-1 than to the paper’s no-skip 12-0. Showing both is also how we resolve that ambiguity.
- Skip-a-month is the Jegadeesh–Titman / AQR convention the paper itself discusses and then *rejects* for mixed-asset data. If 12-1 wins OOS, that is a finding; if it loses, that *supports* Antonacci.
- Inverse-vol (or equal-risk) across modules is the natural next step after 1/N: the stress module has ~2× the vol of credit, so 25/25/25/25 is risk-concentrated in gold/Treasuries/REITs. Paper’s own Table 10 makes this obvious.

We will freeze the baseline as a copy of the paper, then show the alternative on the same OOS window, same costs assumption (zero), same assets. No in-sample tuning of lookbacks.

Backup extra-credit idea if 12-1 is too close to the baseline: add a third risky asset to equities (EM, `VEIEX`) and to stress (TIPS or commodities) — assignment explicitly allows >2 risky assets.

---

## Code / report layout (same pattern as HW4)

```
hw5/
  PLAN.md                          this file
  README.md                        how to reproduce
  requirements.txt
  docs/                            assignment screenshots + paper PDF
  data/raw/                        cached Yahoo/FRED downloads
  data/processed/monthly_returns.csv   the series we ship
  src/dualmomentum/{data,signals,backtest,metrics}.py
  scripts/run_all.py               analysis → outputs/
  scripts/build_report.py          → report/hw5_report.pdf
  outputs/{tables,figures,results.json}
  report/hw5_report.pdf
```

Python 3.12, pandas, yfinance, pandas-datareader/FRED, matplotlib, reportlab. `run_all.py` prefers the cached CSV so a third party does not need network.

Report outline:

1. **Summary page** — four modules, composite, OOS vs paper, extra-credit punchline, all headline numbers.
2. **(a) Data** — table of tickers, sources, start dates, cleaning, mapping to paper indices, limitations (especially NLY vs NAREIT mREIT).
3. **(b) Strategy** — dual-momentum algorithm, timing, 25% weights, no-skip vs skip decision, code pointers / annotated output.
4. **Overlap check** — 2000–2009 vs Table 8; start–2011 vs Table 10 directionally.
5. **(c) Update** — 2012–2026 H1 and full sample; what broke (likely: credit Sharpe, REIT crash in 2020/2022, gold 2013–15, 2022 bonds+stocks).
6. **(d) Extra credit** — 12-1 and/or inverse-vol vs baseline, OOS only.
7. Appendix: utilization, holdings, reproducibility commands.

---

## Open decisions (confirm before coding)

1. **Skip last month?** Paper = **no skip** (12-0). Assignment parenthetical sounds like **skip** (12-1). Recommendation: **baseline = paper (no skip)**; 12-1 is the extra-credit horse race.
2. **Mortgage REIT proxy.** `NLY` from 1997 (covers GFC, single-name risk) vs wait for `REM` (cleaner index, misses 2007–09). Recommendation: **NLY**, disclosed.
3. **Start date.** Common panel from 1997 vs start each module as soon as *its* pair exists (credit/equities could start earlier). Recommendation: **common start** so the composite is well-defined, and mention longer single-module histories in an appendix if useful.
4. **Extra credit.** 12-1 momentum, inverse-vol modules, or extra assets. Recommendation: **12-1 + inverse-vol**, one table, one figure.
5. **Safe haven.** FRED 3m T-bill in every module (paper). Not SHY, not cash zero. Recommendation: **FRED TB3MS**.
