"""
Continuous DiD from your EXISTING merged panel.

Input: the panel CSV you already built (finance + graduation merged,
district-year level, 2016-2022). This script does NOT re-load or
re-process the raw F-33 / OSPI files -- it works entirely from that
one CSV.

Steps:
  1. Dose: pull each district's 2016 per_pupil_spending (already in
     your panel) and compute dose = district's 2016 spending - WA
     state average 2016 spending. This is a fixed, one-time value
     per district.
  2. Check whether any districts have dose ~ 0 (a natural untreated
     group). If not, fall back to the paper's Remark 3.1 approach:
     compare dose groups to the lowest dose (d_L) instead of zero.
  3. Collapse the panel to two periods:
       Y_t1 = 2016 graduation rate (same year as dose baseline)
       Y_t2 = average graduation rate over 2018-2022
       (2017 skipped -- the year EHB 2242 was actually enacted)
  4. Run the regression and report results.
"""

import os
import re
import glob

import numpy as np
import pandas as pd

try:
    import statsmodels.formula.api as smf
    HAVE_STATSMODELS = True
except ImportError:
    HAVE_STATSMODELS = False


# =====================================================
# CONFIG
# =====================================================

PANEL_INPUT = r"C:\Users\HP\Documents\continuous_DiD\data\real\WA_schoolfinance_graduation_panel.csv"
finance_path = r"C:\Users\HP\Documents\continuous_DiD\data\f33_finance"

DOSE_YEAR = 2016
POST_YEARS_SHORT = [2018, 2019]                          # near-term, avoids COVID years
POST_YEARS_LONG = [2018, 2019, 2020, 2021, 2022, 2023, 2024]  # full available window

output_did_path = r"C:\Users\HP\Documents\continuous_DiD\data\real\continuous_did_panel.csv"


def normalize_name(name):
    if pd.isna(name):
        return ""
    n = str(name).lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\bschool district\b", "", n)
    n = re.sub(r"\bschool dist\b", "", n)
    n = re.sub(r"\bpublic schools\b", "", n)
    n = re.sub(r"\bsd\b", "", n)
    n = re.sub(r"\bno\b", "", n)
    n = re.sub(r"\d+", "", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


# =====================================================
# 1. LOAD YOUR EXISTING PANEL (outcomes: graduation rate by year)
# =====================================================

print("Loading existing merged panel:", PANEL_INPUT)
panel = pd.read_csv(PANEL_INPUT)

print("Panel rows:", len(panel))
print("Years present:", sorted(panel["YEAR"].unique().tolist()))

panel["name_key"] = panel["districtname"].apply(normalize_name)


# =====================================================
# 2. BUILD DOSE FROM RAW F-33 LOCAL REVENUE (TLOCREV)
# =====================================================
# This is the direct policy-mechanism dose: local levy revenue per
# pupil in the pre-reform year. EHB 2242's levy cap and Local Effort
# Assistance formula operated directly on this quantity -- it is the
# raw, uncentered analog to AF's Medicare share `m`, not a deviation
# from the state average.

print(f"\nLoading raw F-33 finance files for dose year {DOSE_YEAR}...")

txt_files = glob.glob(finance_path + r"\**\*.txt", recursive=True)

finance_list = []
for file in txt_files:
    try:
        df = pd.read_csv(file, sep="\t", encoding="latin1", low_memory=False)
        finance_list.append(df)
    except Exception as e:
        print("FAILED:", file, e)

finance_raw = pd.concat(finance_list, ignore_index=True)
finance_raw.columns = finance_raw.columns.str.strip()

finance_raw = finance_raw[finance_raw["STABBR"].astype(str).str.strip() == "WA"].copy()
finance_raw = finance_raw[["NAME", "YEAR", "MEMBERSCH", "TLOCREV"]].copy()

finance_raw["YEAR"] = pd.to_numeric(finance_raw["YEAR"], errors="coerce")
finance_raw = finance_raw.dropna(subset=["YEAR"])
finance_raw["YEAR"] = finance_raw["YEAR"].astype(int)
finance_raw["YEAR"] = finance_raw["YEAR"].apply(lambda y: 2000 + y if y < 100 else y)

finance_raw["local_rev_per_pupil"] = (
    pd.to_numeric(finance_raw["TLOCREV"], errors="coerce")
    / pd.to_numeric(finance_raw["MEMBERSCH"], errors="coerce")
)
finance_raw["name_key"] = finance_raw["NAME"].apply(normalize_name)

dose_source = finance_raw[finance_raw["YEAR"] == DOSE_YEAR].copy()
dose_source = dose_source.dropna(subset=["local_rev_per_pupil"])
dose_source = dose_source[dose_source["local_rev_per_pupil"] >= 0]  # drop bad negative rows

dose_df = (
    dose_source.groupby("name_key", as_index=False)
    .agg(dose=("local_rev_per_pupil", "mean"), NAME=("NAME", "first"))
)

print(f"\nDose year: {DOSE_YEAR}")
print(f"Districts with dose (local revenue per pupil) computed: {len(dose_df)}")
print("\nLowest local-revenue-per-pupil districts (least levy reliance):")
print(dose_df.sort_values("dose").head(5).to_string(index=False))
print("\nHighest local-revenue-per-pupil districts (most levy reliance):")
print(dose_df.sort_values("dose").tail(5).to_string(index=False))

# -----------------------------------------------------------------
# Optional outlier trim: same rationale as before -- a few small or
# high-property-wealth districts can raise very high local revenue
# per pupil. Trim using IQR, keep both versions for comparison.
# -----------------------------------------------------------------

q1 = dose_df["dose"].quantile(0.25)
q3 = dose_df["dose"].quantile(0.75)
iqr = q3 - q1
upper_fence = q3 + 1.5 * iqr
lower_fence = max(0, q1 - 1.5 * iqr)  # dose can't go below 0 (it's a raw dollar amount)

outliers = dose_df[(dose_df["dose"] > upper_fence) | (dose_df["dose"] < lower_fence)]
print(f"\nOutlier districts (IQR rule, upper fence={upper_fence:,.0f}): {len(outliers)}")
print(outliers[["NAME", "dose"]].to_string(index=False))

dose_df_trimmed = dose_df[
    (dose_df["dose"] <= upper_fence) & (dose_df["dose"] >= lower_fence)
].copy()

print(f"\nDistricts remaining after trim: {len(dose_df_trimmed)}")

USE_TRIMMED = True
dose_df_full = dose_df.copy()
if USE_TRIMMED:
    dose_df = dose_df_trimmed


# =====================================================
# 3. CHECK FOR AN UNTREATED (dose ~ 0) GROUP
# =====================================================

ZERO_TOLERANCE = dose_df["dose"].std() * 0.05

n_zero = (dose_df["dose"].abs() <= ZERO_TOLERANCE).sum()
print(f"\nDose SD: {dose_df['dose'].std():,.2f}")
print(f"Zero-tolerance band: +/- {ZERO_TOLERANCE:,.2f}")
print(f"Districts within that band of dose=0: {n_zero}")

HAVE_UNTREATED = n_zero >= 5

if HAVE_UNTREATED:
    print(">>> Untreated-ish group found. Using standard D=0 comparison (Eq 4.6 style).")
else:
    print(">>> No meaningful D=0 group -- expected for a statewide reform. Falling back")
    print("    to Remark 3.1: comparing dose groups to the LOWEST dose group (d_L)")
    print("    instead of untreated. Results are relative to d_L, not to zero dose.")


# =====================================================
# 4. COLLAPSE OUTCOME TO TWO PERIODS (using panel you already built)
# =====================================================

baseline = panel[panel["YEAR"] == DOSE_YEAR][["name_key", "graduationrate"]].rename(
    columns={"graduationrate": "Y_t1"}
)
baseline = baseline.groupby("name_key", as_index=False).agg(Y_t1=("Y_t1", "mean"))

if baseline["Y_t1"].notna().sum() == 0:
    earliest_year = panel["YEAR"].min()
    print(f"\nNo graduation data for {DOSE_YEAR} in the panel -- using earliest "
          f"available year ({earliest_year}) as t=1 baseline instead.")
    baseline = panel[panel["YEAR"] == earliest_year][["name_key", "graduationrate"]].rename(
        columns={"graduationrate": "Y_t1"}
    )
    baseline = baseline.groupby("name_key", as_index=False).agg(Y_t1=("Y_t1", "mean"))


def build_did_panel(post_years, label):
    post = (
        panel[panel["YEAR"].isin(post_years)]
        .groupby("name_key", as_index=False)
        .agg(Y_t2=("graduationrate", "mean"))
    )
    collapsed = baseline.merge(post, on="name_key", how="inner")
    collapsed = collapsed.dropna(subset=["Y_t1", "Y_t2"])
    collapsed["delta_Y"] = collapsed["Y_t2"] - collapsed["Y_t1"]

    did = collapsed.merge(dose_df, on="name_key", how="inner")
    print(f"\n[{label}] years {post_years}: {len(did)} districts with dose + outcome")
    return did


did_panel_short = build_did_panel(POST_YEARS_SHORT, "SHORT")
did_panel_long = build_did_panel(POST_YEARS_LONG, "LONG")

did_panel_short.to_csv(output_did_path.replace(".csv", "_short.csv"), index=False)
did_panel_long.to_csv(output_did_path.replace(".csv", "_long.csv"), index=False)
print("\nSaved:", output_did_path.replace(".csv", "_short.csv"))
print("Saved:", output_did_path.replace(".csv", "_long.csv"))


# =====================================================
# 6. REGRESSION -- run for BOTH windows, compare
# =====================================================

def run_regression(did_panel, label):
    if len(did_panel) < 10:
        print(f"\n[{label}] Too few matched districts to run a meaningful regression.")
        return

    print(f"\n--- [{label}] Regression results ---")

    if HAVE_UNTREATED:
        did_panel["treated"] = (did_panel["dose"].abs() > ZERO_TOLERANCE).astype(int)
        if HAVE_STATSMODELS:
            model = smf.ols("delta_Y ~ treated", data=did_panel).fit(cov_type="HC1")
            print(model.summary())
        else:
            print("Install statsmodels: pip install statsmodels --break-system-packages")
    else:
        d_L = did_panel["dose"].min()
        print(f"Lowest dose (d_L) in sample: {d_L:,.2f}")
        print("Comparisons below are RELATIVE TO d_L, not to zero dose.")

        if HAVE_STATSMODELS:
            model = smf.ols("delta_Y ~ dose", data=did_panel).fit(cov_type="HC1")
            print(model.summary())
        else:
            print("Install statsmodels: pip install statsmodels --break-system-packages")


run_regression(did_panel_short, "SHORT: 2018-2019")
run_regression(did_panel_long, "LONG: 2018-2024")

print("\n--- Comparison note ---")
print("If the SHORT and LONG window slopes point the same direction and are of")
print("similar magnitude, that's a robustness signal. If they diverge sharply,")
print("that's informative too -- e.g. COVID-era disruption (2020-2022) or the")
print("gradual EHB 2242 phase-in (full funding only from 2018-19 onward) could")
print("be driving a difference between the two windows. Report both, don't just")
print("pick whichever one looks better.")