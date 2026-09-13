"""Build the full school finance reform panel: district-level per-pupil
spending (1990-2013, missing only 1991) merged with reform event timing
and a dose measure, ready for ContinuousDiD.

first_treat = the year each state's FIRST reform event occurred (per the
eventlist's own newstate==1 flag). States with no reform get first_treat=0.

dose = a district's PRE-REFORM funding gap: its own state's average
per-pupil spending minus the district's own spending, in the nearest
available year BEFORE first_treat. This is deliberately pre-treatment -
see Callaway, Goodman-Bacon & Sant'Anna (2024), Section 3, Assumption 3
(No-Anticipation and Observed Outcomes): dose must be knowable before the
treatment period, the same way the paper's own empirical application uses
each hospital's PRE-existing 1983 Medicare share as dose, not any
post-PPS outcome. An earlier version of this file used post-minus-pre
SPENDING CHANGE as dose - that's circular (using the outcome to build the
treatment variable) and was correctly rejected by ContinuousDiD's own
D>0 validation once tested against a real fit.

Districts already at or above their state's pre-reform average (gap<=0)
are recoded first_treat=0 (not meaningfully "dosed" by an equity-focused
reform) rather than forced into the treated group with an invalid dose.

KNOWN LIMITATIONS (disclose in any writeup):
- Only districts with BOTH a first_treat year AND enough pre-treatment
  panel coverage to find a value before it get a computable dose
- Wide outlier tail remains in the gap measure (state-year average itself
  can be noisy in states with few districts) - worth a second look before
  trusting extreme values
- 1991 has no data anywhere, including in LRS's own original analysis
  (see finance_panel.py docstring)
- Outcome variable is still missing: this panel only has per_pupil_exp,
  which is now used purely as the dose input, not an outcome. LRS's own
  outcome is NAEP student achievement - not yet sourced/merged here.

Dose cleaning (clean_district_years()): raw per-pupil figures have
extreme outliers concentrated in tiny districts. Matches the practitioner
standard found in a PPIC report on California school finance data:
exclude districts under 250 students, and bound per-pupil figures to
20%-500% of each state-year's own average (not a fixed global percentile)
- relative-to-state-year matters here specifically because median
per-pupil spending nearly tripled over this panel (1990: $4,719 -> 2013:
$11,567), so a single global cutoff would unevenly clip different eras.
"""

import logging

import pandas as pd

from finance_panel import build_full_finance_panel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EVENTLIST_PATH = "data/real/eventlist_long_FINAL.xlsx"
OUTPUT_PATH = "data/real/schoolfinance_panel.csv"

MIN_ENROLLMENT = 250  # PPIC standard for CA school finance data
DOSE_BOUND_RATIO = (0.20, 5.00)  # 20%-500% of each state-year's own average per-pupil spending


def load_first_treat(path: str = EVENTLIST_PATH) -> pd.DataFrame:
    """Load the reform event list and extract each state's first reform year."""
    events = pd.read_excel(path)
    events = events.dropna(subset=["fips"])

    first_events = events[events["newstate"] == 1][["fips", "eventyear"]]
    first_events = first_events.rename(columns={"fips": "FIPST", "eventyear": "first_treat"})
    first_events["first_treat"] = first_events["first_treat"].astype(int)

    return first_events


def compute_funding_gap_dose(panel: pd.DataFrame) -> pd.Series:
    """Dose for one district: its state's own pre-reform average per-pupil
    spending minus the district's own spending, in the nearest available
    year BEFORE first_treat. Entirely pre-treatment - see module docstring
    for why this replaced the earlier (circular) post-minus-pre measure.

    Returns a Series indexed by LEAID. Never-treated districts and
    districts lacking any pre-treatment observation are omitted (not
    zero - omitted, so they can be distinguished from a genuine zero gap).
    """
    doses = {}
    for leaid, g in panel.groupby("LEAID"):
        ft = g["first_treat"].iloc[0]
        if ft == 0:
            continue

        pre = g[g["year"] < ft].sort_values("year", ascending=False)
        if len(pre) == 0:
            continue

        pre_year = pre["year"].iloc[0]
        own_spending = pre["per_pupil_exp"].iloc[0]
        state = g["FIPST"].iloc[0]

        state_avg = panel[
            (panel["FIPST"] == state) & (panel["year"] == pre_year)
        ]["per_pupil_exp"].mean()

        doses[leaid] = state_avg - own_spending

    return pd.Series(doses, name="dose")


def clean_district_years(
    panel: pd.DataFrame,
    min_enrollment: int = MIN_ENROLLMENT,
    bound_ratio: tuple = DOSE_BOUND_RATIO,
) -> pd.DataFrame:
    """Drop tiny districts (average enrollment below min_enrollment) and
    drop district-year rows where per_pupil_exp falls outside a ratio of
    that state-year's own average, matching the practitioner standard
    (PPIC, CA school finance data). Run this BEFORE compute_funding_gap_dose
    - cleaning the spending values first, then deriving dose from clean
    data, rather than computing dose from raw data and patching after.
    """
    avg_enrollment = panel.groupby("LEAID")["enrollment"].transform("mean")
    panel = panel[avg_enrollment >= min_enrollment].copy()

    state_year_avg = panel.groupby(["FIPST", "year"])["per_pupil_exp"].transform("mean")
    lo_ratio, hi_ratio = bound_ratio
    panel = panel[
        (panel["per_pupil_exp"] >= lo_ratio * state_year_avg)
        & (panel["per_pupil_exp"] <= hi_ratio * state_year_avg)
    ].copy()

    return panel


def build_schoolfinance_panel(eventlist_path: str = EVENTLIST_PATH) -> pd.DataFrame:
    """Full pipeline: spending panel + first_treat + pre-treatment funding-
    gap dose, one row per district-year, ready for ContinuousDiD (panel
    still needs balancing before fitting - see module docstring).

    Districts with first_treat>0 but no computable positive gap (either no
    pre-treatment coverage, or already at/above their state's pre-reform
    average) are recoded first_treat=0 - see module docstring for why a
    non-positive gap means "not meaningfully dosed" rather than "dose=0".
    """
    panel = build_full_finance_panel()
    panel["FIPST"] = pd.to_numeric(panel["FIPST"], errors="coerce")

    first_treat = load_first_treat(eventlist_path)
    panel = panel.merge(first_treat, on="FIPST", how="left")
    panel["first_treat"] = panel["first_treat"].fillna(0).astype(int)

    panel = clean_district_years(panel)

    doses = compute_funding_gap_dose(panel)
    panel = panel.merge(doses, left_on="LEAID", right_index=True, how="left")

    # Recode as untreated where dose isn't a valid positive gap - see
    # module docstring. ContinuousDiD requires strictly positive dose for
    # every treated unit.
    invalid_dose = panel["dose"].isna() | (panel["dose"] <= 0)
    panel.loc[invalid_dose, "first_treat"] = 0
    panel.loc[invalid_dose, "dose"] = 0

    return balance_panel(panel)


def balance_panel(panel: pd.DataFrame) -> pd.DataFrame:
    """ContinuousDiD requires a balanced panel - keep only districts
    observed in every year present in the data (21 of the 24 calendar
    years span, since 1991/1993/1994 are excluded - see finance_panel.py
    docstring). Drops districts with any gap year, not just short ones."""
    n_years = panel["year"].nunique()
    counts = panel.groupby("LEAID").size()
    balanced_leaids = counts[counts == n_years].index
    return panel[panel["LEAID"].isin(balanced_leaids)].copy()


def save_panel(df: pd.DataFrame, path: str = OUTPUT_PATH) -> None:
    df.to_csv(path, index=False)
    logger.info("Saved data to: %s", path)


if __name__ == "__main__":
    panel = build_schoolfinance_panel()
    save_panel(panel)