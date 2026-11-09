"""Build report/hw5_report.pdf from outputs of scripts/run_all.py."""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.platypus import Image

ROOT = Path(__file__).resolve().parents[1]
OUT, TAB, FIG = ROOT / "outputs", ROOT / "outputs" / "tables", ROOT / "outputs" / "figures"
PDF = ROOT / "report" / "hw5_report.pdf"
PDF.parent.mkdir(exist_ok=True)
res = json.loads((OUT / "results.json").read_text())

AUTHOR = "Young Kim (yk3057)"
ss = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=ss["BodyText"], fontName="Times-Roman", fontSize=10.5, leading=14.5,
                      spaceAfter=5, alignment=TA_JUSTIFY)
CAP = ParagraphStyle("cap", parent=BODY, fontSize=9, leading=12, spaceAfter=3, alignment=TA_CENTER)
H1 = ParagraphStyle("h1", parent=BODY, fontName="Times-Bold", fontSize=13.2, leading=16, spaceBefore=10, spaceAfter=5,
                    alignment=0)
H2 = ParagraphStyle("h2", parent=BODY, fontName="Times-Bold", fontSize=11.1, leading=14.5, spaceBefore=7, spaceAfter=3,
                    alignment=0)
TITLE = ParagraphStyle("title", parent=BODY, fontSize=16.5, leading=20, alignment=TA_CENTER, spaceAfter=2)
CENTER = ParagraphStyle("center", parent=BODY, alignment=TA_CENTER, spaceAfter=1)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=7.6, leading=10, spaceAfter=0, alignment=TA_CENTER)
CELLL = ParagraphStyle("celll", parent=CELL, alignment=0)

story: list = []
MARGIN = 0.75 * inch
W_AVAIL = letter[0] - 2 * MARGIN


def P(text, style=BODY):
    story.append(Paragraph(text, style))


def h1(t):
    story.append(Paragraph(t, H1))


def h2(t):
    story.append(Paragraph(t, H2))


def figure(name, caption, width=W_AVAIL * 0.96):
    p = FIG / name
    w, h = PILImage.open(p).size
    img = Image(str(p), width=width, height=width * h / w)
    story.append(KeepTogether([img, Spacer(1, 2), Paragraph(caption, CAP), Spacer(1, 7)]))


def table(rows, header, col_widths=None, caption=None, font=7.4):
    cell = ParagraphStyle(f"cell{font}", parent=CELL, fontSize=font, leading=font + 2.4)
    left = ParagraphStyle(f"left{font}", parent=cell, alignment=0)
    data = [[Paragraph(str(h), cell) for h in header]]
    for r in rows:
        line = []
        for i, c in enumerate(r):
            line.append(Paragraph(str(c), left if i == 0 else cell))
        data.append(line)
    if col_widths and sum(col_widths) > W_AVAIL:
        col_widths = [c * W_AVAIL / sum(col_widths) for c in col_widths]
    t = Table(data, colWidths=col_widths, repeatRows=1, hAlign="CENTER")
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 0.9, colors.black),
        ("LINEBELOW", (0, 0), (-1, 0), 0.45, colors.black),
        ("LINEBELOW", (0, -1), (-1, -1), 0.9, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 2.4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 2.4),
        ("TOPPADDING", (0, 0), (-1, -1), 1.1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 1.1),
    ]))
    block = ([Paragraph(caption, CAP), Spacer(1, 2)] if caption else []) + [t, Spacer(1, 8)]
    story.append(KeepTogether(block))


def _finite(x):
    return isinstance(x, (int, float)) and x == x and abs(x) != float("inf")


def pct(x, n=5):
    if not _finite(x):
        return "—"
    return f"{100 * x:.{n}f}%"


def f5(x, n=5):
    if not _finite(x):
        return "—"
    return f"{x:.{n}f}"


def st(window, name):
    return res["performance"][window][name]


def row_perf(label, d, trades=True):
    tpy_s = f5(d.get("trades_per_year")) if trades else "—"
    return [label, pct(d["cagr"]), pct(d["vol"]), f5(d["sharpe"]), pct(d["max_dd"]),
            pct(d["pct_positive"], 2), tpy_s]


# ============================================================================= title
P("Systematic Investment Strategies", CENTER)
P("Homework 5", TITLE)
P("Antonacci dual momentum, updated through 2026-06-30", CENTER)
P(AUTHOR, CENTER)
P("Prof. Achilles Venetoulias, Fall 2026 &nbsp;&nbsp; November 9, 2026", CENTER)
story.append(Spacer(1, 6))

full = st("full", "composite_dual")
oos = st("oos_2012_2026", "composite_dual")
sub = st("sub_2000_2009", "composite_dual")
t8 = {r["module"]: r for r in res["paper_table8"]}
s0, s1 = res["sample"]["first_holding"], res["sample"]["last_holding"]
nmo = res["sample"]["n_months"]

h1("Summary of answers")
P(f"<b>(a) Data.</b> Monthly total-return series, month-end, {s0} to {s1} "
  f"({nmo} holding months after a 12-month lookback). Four modules, each with two risky assets and the same "
  "T-bill safe haven: equities VFINX/VGTSX, credit VWEHX/VFICX, real estate VGSIX/NLY, stress World Bank gold/"
  "VUSTX. T-bills are Kenneth French’s monthly RF (1-month bill return), the closest public analogue of the "
  "paper’s BofA Merrill Lynch 3-month T-bill index. Sources, cleaning, and the NLY/gold caveats are in §1.")
P(f"<b>(b) Implementation.</b> Dual momentum as in Antonacci (2013): 12-month compounded total return with "
  "<i>no</i> skip-a-month (the paper’s explicit choice), relative winner inside each module, then a T-bill hurdle "
  "for absolute momentum. Signal at month-end <i>t</i>, held during <i>t</i>+1. Composite is 25% each module, "
  f"rebalanced monthly. Full-sample composite: CAGR {pct(full['cagr'])}, vol {pct(full['vol'])}, "
  f"Sharpe {f5(full['sharpe'])}, max DD {pct(full['max_dd'])}.")
P(f"<b>(c) vs the paper.</b> On the assignment’s 1/00–12/09 window the four modules are in the same ballpark as "
  f"Table 8, especially REITs ({pct(t8['reits']['ours_cagr'])} vs paper {pct(t8['reits']['paper_cagr'])}). "
  f"The composite earns {pct(sub['cagr'])} with vol {pct(sub['vol'])} and Sharpe {f5(sub['sharpe'])}. "
  f"True out-of-sample (2012-01 to 2026-06) the composite slows to CAGR {pct(oos['cagr'])}, Sharpe {f5(oos['sharpe'])}, "
  f"and lags US equities ({pct(st('oos_2012_2026','US')['cagr'])}) and even 60/40 "
  f"({pct(st('oos_2012_2026','sixty_forty')['cagr'])}). Absolute momentum still does what it is for: GFC total "
  f"return {pct(st('gfc','composite_dual')['total_return'])} vs US {pct(st('gfc','US')['total_return'])}. "
  "It does not add return in a long equity bull, and it is too slow for COVID (a two-month crash inside a positive "
  "12-month trend).")
ec = st("oos_2012_2026", "composite_12_1")
iv = st("oos_2012_2026", "composite_invvol")
iv1 = st("oos_2012_2026", "composite_12_1_invvol")
P(f"<b>(d) Extra credit.</b> Two changes, frozen before looking at 2012–2026. Skip-last-month 12-1 dual, 1/N: OOS "
  f"CAGR {pct(ec['cagr'])} and Sharpe {f5(ec['sharpe'])} vs the paper rule’s {pct(oos['cagr'])} / {f5(oos['sharpe'])}. "
  f"Inverse-vol module weights make it worse (OOS CAGR {pct(iv['cagr'])}) because they load 46.851% on the low-vol "
  f"credit sleeve and starve the high-vol modules the paper wanted. 12-1 plus inverse-vol is in between "
  f"(CAGR {pct(iv1['cagr'])}, max DD {pct(iv1['max_dd'])}). The improvement that survives is 12-1, not risk parity.")

# ============================================================================= 1 data
h1("1. Data")
P("The paper’s empirical work uses institutional total-return indices from January 1974 through December 2011 "
  "(Antonacci 2013, §2). Those series are not public. I map each paper index to a live total-return vehicle that "
  "(i) starts before 2011, (ii) covers 2007–09, (iii) runs through 2026-06-30, and (iv) is downloadable by a third "
  "party. Mutual-fund adjusted closes beat ETFs on history. All risky-asset returns are Yahoo Finance "
  "<i>auto-adjusted</i> closes (splits and dividends), sampled at calendar month-end (last available print). "
  "No price interpolation. No expense-ratio add-back: live vehicles already embed fees, so the update is net of "
  "the costs an implementer would have paid, unlike the paper (no transaction costs, institutional index levels).")

table(
    [
        ["Equities", "US large cap", "MSCI US", "VFINX", "1976 / 1980 on Yahoo"],
        ["Equities", "World ex-US", "EAFE+ (EAFE then ACWI ex-US)", "VGTSX", "Apr 1996; includes EM"],
        ["Credit", "High yield", "BofA ML US Cash Pay HY", "VWEHX", "1978 / 1980 on Yahoo"],
        ["Credit", "Intermediate IG", "Barclays US Intermediate Credit", "VFICX", "Oct 1993"],
        ["Real estate", "Equity REITs", "FTSE NAREIT equity REITs", "VGSIX", "May 1996"],
        ["Real estate", "Mortgage REITs", "FTSE NAREIT mortgage REITs", "NLY", "Oct 1997; single name"],
        ["Stress", "Gold", "London PM gold fix", "WB Pink Sheet gold", "monthly average USD/oz"],
        ["Stress", "Long Treasuries", "Barclays US Long Treasury", "VUSTX", "May 1986"],
        ["Safe haven", "T-bills", "BofA ML 3-month T-bill index", "French RF", "monthly 1m T-bill return"],
        ["Benchmark", "US 60/40", "World 60/40 analogue", "0.6 VFINX + 0.4 VBMFX", "monthly rebalanced"],
    ],
    ["Module", "Role", "Paper series", "Series used", "History / note"],
    [62, 78, 130, 88, 110],
    caption="Table 1: Mapping from Antonacci (2013) §2 to public total-return series.",
    font=7.0,
)

h2("1.1 Why these pairs")
P("Each module needs two risky assets that are different views of the same risk premium, plus one non-risky "
  "safe haven (assignment (a)). Equities: US vs rest-of-world, the paper’s pair; VGTSX is ACWI ex-US rather than "
  "EAFE, so after 1987 it is closer to the paper’s EAFE+ than EFA would be. Credit: high yield vs intermediate "
  "investment-grade, matching Table 3’s duration-matched credit-risk contrast (HY vol comes from default risk, "
  "not duration). Real estate: equity REITs vs a mortgage REIT. Stress: gold (flight from uncertainty) vs long "
  "Treasuries (flight to quality). The same T-bill is the absolute-momentum hurdle and the cash sleeve in every "
  "module, as the paper does and the assignment allows.")

h2("1.2 Two imperfect mappings, stated plainly")
P("<b>Mortgage REITs.</b> The paper uses the NAREIT mortgage-REIT <i>index</i>. The iShares mREIT ETF REM starts "
  "May 2007 as a fund but the liquid history that Yahoo returns cleanly from 2011, which would drop the GFC. I use "
  "Annaly (NLY), the largest agency mREIT, from October 1997. That is a single leveraged name, not an index: "
  "idiosyncratic rate, prepayment, and dividend-cut risk sit in the REIT module. On 2000–09 the dual REIT sleeve "
  f"still landed close to Table 8 ({pct(t8['reits']['ours_cagr'])} vs {pct(t8['reits']['paper_cagr'])}), which is "
  "the check I care about, but the mapping is the weakest in the panel.")
P("<b>Gold.</b> FRED’s LBMA PM/AM fix series (GOLDPMGBD228NLBM / GOLDAMGBD228NLBM) were pulled in January 2022 "
  "with the rest of the ICE Benchmark Administration files; the old fredgraph.csv URLs 404. I use the World Bank "
  "Pink Sheet monthly average gold price in USD/oz (public-domain compilation, datasets/gold-prices, through "
  "2026-10). That is a <i>monthly average</i>, not the paper’s month-end London PM print, so gold’s measured vol "
  "is slightly smoothed. Timing is still valid: the June average is known at June month-end and is used only for "
  "the July holding. Gold pays no dividend; percent changes in the USD/oz series are the total return, as in the "
  "paper.")
P("<b>T-bills.</b> French RF is a true monthly T-bill <i>return</i>, not a yield. I prefer it to converting FRED "
  "TB3MS with (1+y)^(1/12)−1. French RF is a one-month bill; the paper used a three-month bill index. "
  "For a 12-month ranking the difference is second-order. French RF in this file runs through 2026-09, so no "
  "yield conversion is needed inside the 2026-06 sample.")

h2("1.3 Sample")
P(f"The binding start is NLY (1997-10-31). Twelve monthly returns plus a one-month implementation lag give a "
  f"first holding month of {s0}. Last holding month is {s1} ({nmo} months, "
  f"{nmo/12:.5f} years). That covers the GFC, the assignment’s 1/00–12/09 subsample, overlap with the paper "
  "through 2011-12, and 14.5 years of true out-of-sample. Processed prices and returns are in "
  "<font face='Courier'>data/processed/</font>; a third party does not need Yahoo.")

# ============================================================================= 2 strategy
h1("2. Dual momentum, as implemented")
P("Antonacci’s two-stage rule, applied independently in each module at month-end <i>t</i>, after <i>R<sub>t</sub></i> "
  "is known:")
P("1. <b>Relative momentum.</b> Among the module’s two risky assets, pick the one with the higher trailing "
  "12-month compounded total return "
  "m<sub>i,t</sub> = Π<sub>k=0..11</sub> (1+R<sub>i,t−k</sub>) − 1.")
P("2. <b>Absolute momentum.</b> If that winner also beat T-bills over the same 12 months, hold the winner during "
  "month <i>t</i>+1. Otherwise hold T-bills during <i>t</i>+1.")
P("3. <b>Composite.</b> Equal 25% in each of the four module returns, rebalanced every month. Antonacci (footnote 7) "
  "cites DeMiguel, Garlappi and Uppal (2009): 1/N beats estimated optimal weights out of sample. I do not "
  "re-optimize.")
P("The paper is explicit (p. 4) that it does <i>not</i> skip the last month, even though equity-momentum papers "
  "usually do, because the universe mixes gold, bonds and REITs. That is the baseline. The assignment’s "
  "parenthetical “(without last-month reversal effects)” is the 12-1 alternative, run as extra credit in §5. "
  "Look-ahead is barred by construction: the holding during month <i>t</i> equals the choice made at <i>t</i>−1. "
  "Five unit tests in <font face='Courier'>tests/test_lookahead.py</font> pin down the lag, the skip, the T-bill "
  "overlay, and the inverse-vol lag.")
P("I also compute the paper’s three natural comparators (Table 14): relative-only (always hold the winner), "
  "absolute-only (each of the eight assets vs T-bills, then 1/8), and no-momentum 1/8 of the eight risky assets. "
  "60/40 is 60% VFINX + 40% VBMFX, monthly. Section 12 factor alphas are not run.")

h2("2.1 Statistics")
P("CAGR is geometric, (product of (1+R))^(12/n) − 1. Vol is sample monthly standard deviation × √12 (ddof=1). "
  "Sharpe is mean excess monthly return over T-bills, divided by the sample standard deviation of that excess, "
  "times √12 — the usual arithmetic Sharpe. I also store (CAGR − rf CAGR)/vol as sharpe_geom, which is closer to "
  "how practitioner tables sometimes look; headline Sharpes in this write-up are the arithmetic ones. Max "
  "drawdown is peak-to-trough on the month-end wealth index. % profit months is the fraction of months with "
  "R&gt;0. Trades/year count holding <i>changes</i> after the first valid month, divided by years. Kurtosis is "
  "Pearson (normal = 3), matching Table 10.")

# ============================================================================= 3 overlap
h1("3. Overlap with the paper")
h2("3.1 Table 8, January 2000 – December 2009")
P("This is the subsample the assignment flags if the data reach 2007. Ours do. The paper’s decade table is the "
  "cleanest apples-to-apples check, because it does not require 1974 history.")

def t8row(mod, label):
    r = t8[mod]
    return [label, pct(r["paper_cagr"]), pct(r["ours_cagr"]), pct(r["paper_vol"]), pct(r["ours_vol"]),
            f5(r["paper_sharpe"]), f5(r["ours_sharpe"]), pct(r["paper_max_dd"]), pct(r["ours_max_dd"])]

table(
    [
        t8row("equities", "Equities dual"),
        t8row("credit", "Credit dual"),
        t8row("reits", "REIT dual"),
        t8row("stress", "Stress dual"),
        ["Composite (ours)", "—", pct(sub["cagr"]), "—", pct(sub["vol"]),
         "—", f5(sub["sharpe"]), "—", pct(sub["max_dd"])],
    ],
    ["Module", "Paper CAGR", "Ours CAGR", "Paper vol", "Ours vol", "Paper Sh.", "Ours Sh.", "Paper DD", "Ours DD"],
    [88, 62, 62, 58, 58, 52, 52, 62, 58],
    caption="Table 2: Dual-momentum modules, Jan 2000 – Dec 2009, vs Antonacci Table 8. Paper Sharpe methodology "
            "is not fully specified; ours is arithmetic excess/vol. Composite is not in Table 8.",
    font=7.0,
)

P(f"Directionally the paper’s ranking survives: REITs are the high-return high-vol sleeve "
  f"({pct(t8['reits']['ours_cagr'])} vs paper {pct(t8['reits']['paper_cagr'])}), credit is the low-vol Sharpe engine, "
  "equities and stress sit in between. Every sleeve is a bit weaker than the paper, which is what you should "
  "expect from live mutual funds with fees vs institutional indices, a single-name mREIT, and monthly-average "
  "gold. The gaps are 1.8–2.3 percentage points of CAGR except REITs (−0.67 pp). I would not call this a "
  "replication of the 1974–2011 Table 10 composite (14.93% / 1.07 Sharpe) — different start date, different "
  f"assets — but it is close enough on the requested decade that the <i>rule</i> is the same rule. Our 2000–09 "
  f"composite did {pct(sub['cagr'])} at {pct(sub['vol'])} vol, Sharpe {f5(sub['sharpe'])}, max DD {pct(sub['max_dd'])}.")

h2("3.2 Utilization vs Table 11")
u = res["utilization"]["full"]
P("Paper, 1974–2011 (Table 11): equities spent 22.6% of months in T-bills, credit 25.2%, REITs 26.3%, stress "
  "17.8%. Full-sample utilization here:")

table(
    [
        ["Equities", pct(u["equities"].get("US", 0), 3), pct(u["equities"].get("INTL", 0), 3),
         pct(u["equities"].get("TBILL", 0), 3)],
        ["Credit", pct(u["credit"].get("HY", 0), 3), pct(u["credit"].get("IG", 0), 3),
         pct(u["credit"].get("TBILL", 0), 3)],
        ["REITs", pct(u["reits"].get("EREIT", 0), 3), pct(u["reits"].get("MREIT", 0), 3),
         pct(u["reits"].get("TBILL", 0), 3)],
        ["Stress", pct(u["stress"].get("GOLD", 0), 3), pct(u["stress"].get("TREAS", 0), 3),
         pct(u["stress"].get("TBILL", 0), 3)],
    ],
    ["Module", "Risky A (US / HY / EREIT / GOLD)", "Risky B (INTL / IG / MREIT / TREAS)", "T-bills"],
    [70, 175, 185, 70],
    caption="Table 3: Fraction of months each asset is held, dual 12-0, full sample.",
    font=7.2,
)

cash = res["cash_occupancy_full"]
P(f"T-bill occupancy is similar to the paper, a bit lower (15.7–21.1% vs 17.8–26.3%). The mix inside the risky "
  f"sleeves is more US- and gold-heavy than 1974–2011, which is the post-1998 sample, not a bug: US beat "
  f"international for most of 2010–2026, and gold had two long bulls. All four modules sat in T-bills on "
  f"{pct(cash['modules_in_tbill_4'], 3)} of months (paper 3.5%); two or more were in T-bills on "
  f"{pct(cash['modules_in_tbill_2']+cash['modules_in_tbill_3']+cash['modules_in_tbill_4'], 3)} of months.")
figure("utilization.png", "Figure 1: Asset utilization by module, full sample.")
figure("holdings.png", "Figure 2: Month-end holdings. Grey = T-bills. The 2008 and 2022 cash spells are visible "
       "in equities; gold dominates the stress module after 2023.")

h2("3.3 The GFC, which is why absolute momentum exists")
gfc_d = st("gfc", "composite_dual")
gfc_r = st("gfc", "composite_relative")
gfc_us = st("gfc", "US")
gfc_64 = st("gfc", "sixty_forty")
P(f"October 2007 – March 2009, total (not annualized) return: dual composite {pct(gfc_d['total_return'])}, "
  f"relative-only composite {pct(gfc_r['total_return'])}, 1/8 risky {pct(st('gfc','ew8')['total_return'])}, "
  f"60/40 {pct(gfc_64['total_return'])}, US equities {pct(gfc_us['total_return'])}. Dual lost less than one percent "
  f"over the GFC window; US lost almost half. That is Table 1 / Figure 1 of the paper, on public funds. The gap "
  f"between dual and relative-only ({pct(gfc_d['total_return'])} vs {pct(gfc_r['total_return'])}) is the T-bill "
  f"overlay. Stress was the only module with a positive GFC total return "
  f"({pct(st('gfc','stress_dual')['total_return'])}).")

# ============================================================================= 4 update
h1("4. The update: full sample and 2012–2026")
P("The homework is not to re-print 1974–2011. It is to ask whether the same construction still does, after "
  "publication, what Antonacci said it did.")

def prow(label, key, window="full"):
    return row_perf(label, st(window, key))

table(
    [
        prow("US (VFINX)", "US"),
        prow("International (VGTSX)", "INTL"),
        prow("Equities relative", "equities_rel"),
        prow("Equities dual", "equities_dual"),
        prow("High yield", "HY"),
        prow("Intermediate IG", "IG"),
        prow("Credit relative", "credit_rel"),
        prow("Credit dual", "credit_dual"),
        prow("Equity REITs", "EREIT"),
        prow("NLY (mREIT)", "MREIT"),
        prow("REITs relative", "reits_rel"),
        prow("REITs dual", "reits_dual"),
        prow("Gold", "GOLD"),
        prow("Long Treasuries", "TREAS"),
        prow("Stress relative", "stress_rel"),
        prow("Stress dual", "stress_dual"),
        prow("1/8 risky, no momentum", "ew8"),
        prow("60/40", "sixty_forty"),
        prow("T-bills", "TBILL"),
        prow("Composite relative", "composite_relative"),
        prow("Composite absolute", "composite_absolute"),
        prow("Composite dual (paper rule)", "composite_dual"),
    ],
    ["Strategy", "CAGR", "Vol", "Sharpe", "Max DD", "% + months", "Trades/yr"],
    [145, 62, 58, 52, 62, 62, 58],
    caption=f"Table 4: Full sample {s0} to {s1} ({nmo} months). Sharpe is arithmetic excess over T-bills. "
            "Trades/year is switches after the first holding.",
    font=7.0,
)

P(f"Three facts from Table 4, relative to Antonacci’s Table 10 / Table 14. First, dual still beats buy-and-hold "
  f"<i>on risk</i>: composite vol {pct(full['vol'])} vs US {pct(st('full','US')['vol'])} vs 1/8 "
  f"{pct(st('full','ew8')['vol'])}, max DD {pct(full['max_dd'])} vs US {pct(st('full','US')['max_dd'])}. "
  f"Second, dual no longer beats relative-only on return. Relative composite CAGR {pct(st('full','composite_relative')['cagr'])} "
  f"vs dual {pct(full['cagr'])}; Sharpes are almost the same ({f5(st('full','composite_relative')['sharpe'])} vs "
  f"{f5(full['sharpe'])}). The T-bill overlay bought a smaller left tail "
  f"(DD {pct(full['max_dd'])} vs {pct(st('full','composite_relative')['max_dd'])}) and paid for it in bull-market "
  f"CAGR. Third, the REIT sleeve is where the paper and the update disagree most: relative REITs "
  f"{pct(st('full','reits_rel')['cagr'])} vs dual {pct(st('full','reits_dual')['cagr'])}. In Table 6 of the paper "
  "those two were 16.80% and 16.78%. Here the cash overlay on NLY/VGSIX is expensive. That is partly NLY, partly "
  "the 2022–2023 REIT bear being slow enough for 12-month momentum to stay long and then getting whipped.")

figure("growth_full.png",
       "Figure 3: Growth of $100, log scale, full sample. Dual (blue) tracks relative (orange) through 2011, then "
       "lags as the T-bill overlay spends more time out of equities in a long bull market.")
figure("growth_modules.png",
       "Figure 4: The four dual-momentum modules and the 1/N composite. Credit is the ballast; REITs and stress "
       "are the vol.")
figure("drawdown_composite.png",
       "Figure 5: Composite month-end drawdown. The worst print is not the GFC; it is 2022–2024, when stocks, "
       "credit and REITs fell together and 12-month absolute momentum was late.")

h2("4.1 Out of sample, January 2012 – June 2026")
table(
    [
        prow("US (VFINX)", "US", "oos_2012_2026"),
        prow("60/40", "sixty_forty", "oos_2012_2026"),
        prow("1/8 risky", "ew8", "oos_2012_2026"),
        prow("Equities dual", "equities_dual", "oos_2012_2026"),
        prow("Credit dual", "credit_dual", "oos_2012_2026"),
        prow("REITs dual", "reits_dual", "oos_2012_2026"),
        prow("Stress dual", "stress_dual", "oos_2012_2026"),
        prow("Composite relative", "composite_relative", "oos_2012_2026"),
        prow("Composite dual", "composite_dual", "oos_2012_2026"),
        prow("Composite 12-1 (extra credit)", "composite_12_1", "oos_2012_2026"),
    ],
    ["Strategy", "CAGR", "Vol", "Sharpe", "Max DD", "% + months", "Trades/yr"],
    [155, 62, 58, 52, 62, 62, 58],
    caption="Table 5: True out-of-sample window, Jan 2012 – Jun 2026 (174 months).",
    font=7.0,
)

P(f"This is the result that should change how one reads the paper. US equities compounded at "
  f"{pct(st('oos_2012_2026','US')['cagr'])} with Sharpe {f5(st('oos_2012_2026','US')['sharpe'])}. Dual composite "
  f"compounded at {pct(oos['cagr'])} with Sharpe {f5(oos['sharpe'])}. 60/40 made {pct(st('oos_2012_2026','sixty_forty')['cagr'])}. "
  f"Relative-only composite made {pct(st('oos_2012_2026','composite_relative')['cagr'])} — so the drag is not "
  "“momentum died,” it is specifically the <i>absolute</i> overlay in a decade-plus bull with short, sharp "
  "drawdowns. Split the OOS in two: 2012–2019 dual CAGR "
  f"{pct(st('oos_2012_2019','composite_dual')['cagr'])} vs US {pct(st('oos_2012_2019','US')['cagr'])}; "
  f"2020–2026 H1 dual {pct(st('oos_2020_2026','composite_dual')['cagr'])} vs US {pct(st('oos_2020_2026','US')['cagr'])}. "
  "Both halves, same story.")
P("Module-level OOS is not uniform. Credit dual still looks like the paper: "
  f"CAGR {pct(st('oos_2012_2026','credit_dual')['cagr'])}, vol {pct(st('oos_2012_2026','credit_dual')['vol'])}, "
  f"Sharpe {f5(st('oos_2012_2026','credit_dual')['sharpe'])}, max DD only {pct(st('oos_2012_2026','credit_dual')['max_dd'])}. "
  f"REIT dual is the failure: CAGR {pct(st('oos_2012_2026','reits_dual')['cagr'])}, max DD "
  f"{pct(st('oos_2012_2026','reits_dual')['max_dd'])}. Equities dual "
  f"{pct(st('oos_2012_2026','equities_dual')['cagr'])} vs buy-and-hold US {pct(st('oos_2012_2026','US')['cagr'])} "
  "is the cost of being in T-bills during 2015–16, 2018, 2022 and parts of 2022–23 while the 12-month window "
  "reset. Stress dual "
  f"{pct(st('oos_2012_2026','stress_dual')['cagr'])} beat long Treasuries "
  f"({pct(st('oos_2012_2026','TREAS')['cagr'])}) by sitting in gold, which is the module working.")

figure("growth_oos.png",
       "Figure 6: OOS growth of $100. US equities (purple) pull away. Dual (blue) ends near the 1/8 risky portfolio "
       "and below 60/40 — the opposite of Table 10’s ranking.")
figure("rolling_sharpe.png",
       "Figure 7: Rolling 36-month Sharpe of the dual composite vs T-bills. The post-publication window is a "
       "sequence of near-zero and negative prints around 2015, 2018 and 2022, not a stable 1.0.")

h2("4.2 Three crises the 12-month rule was and was not built for")
table(
    [
        ["GFC Oct 07 – Mar 09",
         pct(st("gfc", "composite_dual")["total_return"]),
         pct(st("gfc", "composite_relative")["total_return"]),
         pct(st("gfc", "ew8")["total_return"]),
         pct(st("gfc", "sixty_forty")["total_return"]),
         pct(st("gfc", "US")["total_return"])],
        ["COVID Feb–Mar 2020",
         pct(st("covid", "composite_dual")["total_return"]),
         pct(st("covid", "composite_relative")["total_return"]),
         pct(st("covid", "ew8")["total_return"]),
         pct(st("covid", "sixty_forty")["total_return"]),
         pct(st("covid", "US")["total_return"])],
        ["2022 hiking cycle",
         pct(st("hikes_2022", "composite_dual")["total_return"]),
         pct(st("hikes_2022", "composite_relative")["total_return"]),
         pct(st("hikes_2022", "ew8")["total_return"]),
         pct(st("hikes_2022", "sixty_forty")["total_return"]),
         pct(st("hikes_2022", "US")["total_return"])],
    ],
    ["Window (total return)", "Dual", "Relative", "EW8", "60/40", "US"],
    [130, 70, 70, 70, 70, 70],
    caption="Table 6: Crisis windows, total return (not annualized). Dual and relative are identical in COVID "
            "because 12-month absolute momentum was still positive.",
    font=7.2,
)
figure("episodes.png", "Figure 8: Same crisis windows as Table 6.")
P("GFC: the textbook case. A long, deep, correlated risk-off that 12-month absolute momentum can see. COVID: "
  "the opposite. The crash is two months inside a still-positive 12-month window, so dual = relative = long "
  f"equities and REITs, and the composite drops {pct(st('covid','composite_dual')['total_return'])} while US drops "
  f"{pct(st('covid','US')['total_return'])}. A 12-month timer cannot help you in March 2020; a 3-month timer might, "
  "and Table 9 of the paper already showed that 3-month formation is worse on average. 2022: stocks and bonds "
  "fall together, so 60/40 does not diversify. Dual loses less than 60/40 "
  f"({pct(st('hikes_2022','composite_dual')['total_return'])} vs {pct(st('hikes_2022','sixty_forty')['total_return'])}) "
  f"because credit goes to T-bills and stress prefers gold to Treasuries, but REITs still lose "
  f"{pct(st('hikes_2022','reits_dual')['total_return'])} and the composite’s worst drawdown of the whole sample "
  "is this episode plus the 2023–24 hangover, not 2008.")

h2("4.3 What I would actually conclude")
P("Antonacci’s qualitative claims that survive 2012–2026: (i) modules keep you from putting the whole book in "
  "one correlated winner; (ii) absolute momentum cuts left-tail damage in slow bears (GFC, parts of 2022); "
  "(iii) credit dual momentum is still a high Sharpe, low DD sleeve. The quantitative claim that does not "
  "survive: that combining relative and absolute momentum raises return <i>and</i> Sharpe relative to the assets "
  "and to 1/N (Tables 10 and 14). After publication, in public funds, dual is a risk overlay on a relative-momentum "
  "book. It is not an alpha machine vs 60/40 or vs US equities. Anyone running this live in 2012–2026 underperformed "
  "a lazy 60/40 on CAGR and only roughly matched it on Sharpe "
  f"({f5(oos['sharpe'])} vs {f5(st('oos_2012_2026','sixty_forty')['sharpe'])}).")

# ============================================================================= 5 extra credit
h1("5. Extra credit: 12-1 lookback and inverse-vol weights")
P("Two changes, specified in the plan before OOS numbers were computed. No lookback search, no in-sample "
  "tuning of the vol window.")
P("<b>12-1.</b> Same dual rule, but m<sub>i,t</sub> uses months <i>t</i>−12 through <i>t</i>−1, skipping month "
  "<i>t</i>. This is the Jegadeesh–Titman / AQR convention the paper discussed and rejected for mixed assets, and "
  "it is the reading of the assignment’s “without last-month reversal effects.”")
P("<b>Inverse-vol 1/N replacement.</b> At t, estimate each module’s trailing 12-month realized vol from that "
  "module’s dual returns through t, then hold weights ∝ 1/σ during t+1. No caps. This asks whether 25/25/25/25 "
  "is leaving Sharpe on the table because Table 10’s stress sleeve has ~2× credit vol.")

table(
    [
        prow("Dual 12-0, 1/N (paper)", "composite_dual", "oos_2012_2026"),
        prow("Dual 12-1, 1/N", "composite_12_1", "oos_2012_2026"),
        prow("Dual 12-0, inv. vol", "composite_invvol", "oos_2012_2026"),
        prow("Dual 12-1, inv. vol", "composite_12_1_invvol", "oos_2012_2026"),
        prow("Relative 12-0, 1/N", "composite_relative", "oos_2012_2026"),
    ],
    ["Construction, OOS 2012–2026 H1", "CAGR", "Vol", "Sharpe", "Max DD", "% + months", "Trades/yr"],
    [160, 58, 54, 50, 62, 62, 54],
    caption="Table 7: Extra-credit horse race, frozen specifications, same assets, zero costs.",
    font=7.0,
)
table(
    [
        prow("Dual 12-0, 1/N", "composite_dual"),
        prow("Dual 12-1, 1/N", "composite_12_1"),
        prow("Dual 12-0, inv. vol", "composite_invvol"),
        prow("Dual 12-1, inv. vol", "composite_12_1_invvol"),
        prow("Relative 12-0, 1/N", "composite_relative"),
    ],
    ["Construction, full sample", "CAGR", "Vol", "Sharpe", "Max DD", "% + months", "Trades/yr"],
    [160, 58, 54, 50, 62, 62, 54],
    caption="Table 8: Same horse race on the full sample (12-1 and inv-vol start a few months later).",
    font=7.0,
)

wbar = res["invvol_mean_weights"]
P(f"Skip-a-month wins, out of sample and in sample. OOS CAGR rises from {pct(oos['cagr'])} to {pct(ec['cagr'])}, "
  f"Sharpe from {f5(oos['sharpe'])} to {f5(ec['sharpe'])}, max DD shrinks from {pct(oos['max_dd'])} to "
  f"{pct(ec['max_dd'])}. Full-sample Sharpe goes from {f5(full['sharpe'])} to "
  f"{f5(st('full','composite_12_1')['sharpe'])}. Last-month reversal is not just an equity microstructure story; "
  "in this mixed-asset book, including month t in a 12-month rank that is then held during t+1 adds noise. The "
  "paper’s consistency argument for not skipping is reasonable and I kept it as the baseline. The data after "
  "2011 disagree with it.")
P(f"Inverse-vol loses on the thing the paper was designed to do. Mean weights: credit {pct(wbar['credit'], 3)}, "
  f"equities {pct(wbar['equities'], 3)}, stress {pct(wbar['stress'], 3)}, REITs {pct(wbar['reits'], 3)}. "
  "That is mechanically correct — credit vol is ~4% — and it is the opposite of Antonacci’s premise that you "
  "<i>want</i> the high-vol sleeves, with a trend overlay, because that is where the risk premium lives. "
  f"OOS inv-vol CAGR {pct(iv['cagr'])} with a left tail that is actually worse than 1/N in 2020 "
  f"(kurtosis {f5(st('oos_2012_2026','composite_invvol')['kurtosis'])} Pearson). Combining 12-1 with inverse-vol "
  f"repairs some of the DD ({pct(iv1['max_dd'])} OOS) but still trails 12-1 1/N on CAGR. I would not take it.")
figure("extra_credit_oos.png",
       "Figure 9: Extra credit, OOS. 12-1 (orange) and relative-only (purple) pull away from the paper rule (blue). "
       "Inverse-vol (green) is the laggard.")
figure("extra_credit_full.png", "Figure 10: Extra credit, full sample. Same ranking.")
figure("invvol_weights.png",
       "Figure 11: Inverse-vol weights over time. Credit (second band) is structurally overweight; REIT and stress "
       "are structurally underweight. That is why inv-vol fights the strategy.")

P("If I had to ship one change: switch the baseline lookback from 12-0 to 12-1, keep 1/N modules, keep the T-bill "
  "hurdle. Do not risk-parity the modules.")

# ============================================================================= 6 limitations
h1("6. Limitations")
P("Live funds, not the paper’s indices: Vanguard expense ratios and NLY’s single-name risk sit in the returns. "
  "That biases us <i>against</i> matching Table 10, which is the conservative direction for an update. Gold is a "
  "monthly average, not a PM fix. No transaction costs; paper turnover is 1.2–1.8 switches per module-year here "
  "too, so costs are small relative to the OOS gap vs US equities. 60/40 uses US bonds, not the paper’s world "
  "60/40. The composite is not volatility-targeted at the asset level. I did not walk the strategy through a "
  "capacity or tax overlay. French RF is a 1-month bill. None of these explain away the OOS underperformance vs "
  "US equities; they do mean Table 2 is a cousin of Table 8, not a clone.")

h1("7. Reproducibility")
P("Python 3.12, from <font face='Courier'>hw5/</font>:")
P("<font face='Courier'>python3.12 -m venv .venv &amp;&amp; .venv/bin/pip install -r requirements.txt<br/>"
  "MPLCONFIGDIR=.mplcache .venv/bin/python -m pytest tests/ -q<br/>"
  "MPLCONFIGDIR=.mplcache .venv/bin/python scripts/run_all.py<br/>"
  "MPLCONFIGDIR=.mplcache .venv/bin/python scripts/build_report.py</font>", CAP)
P("Network is required only for a fresh download (<font face='Courier'>python scripts/run_all.py --download</font>). "
  "The graded path uses <font face='Courier'>data/processed/monthly_returns.csv</font>. Timing convention, "
  "lookbacks and inverse-vol lag are unit-tested. Paper PDF: "
  "<font face='Courier'>docs/antonacci_2013_dual_momentum.pdf</font>.")


def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFont("Times-Roman", 8.5)
    canvas.drawString(MARGIN, 0.45 * inch, f"SIS HW5, {AUTHOR}")
    canvas.drawRightString(letter[0] - MARGIN, 0.45 * inch, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(PDF),
    pagesize=letter,
    leftMargin=MARGIN,
    rightMargin=MARGIN,
    topMargin=0.7 * inch,
    bottomMargin=0.7 * inch,
    title="SIS Homework 5",
    author=AUTHOR,
)
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"wrote {PDF}")
