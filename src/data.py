import pandas as pd
import numpy as np 
from diff_diff import ContinuousDiD, CallawaySantAnna, generate_continuous_did_data
from matplotlib.pyplot import figure, show
try:
    import matplotlib.pyplot as plt
    plt.style.use('seaborn-v0_8-whitegrid')
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("matplotlib not installed - visualization examples will be skipped")
    
    


"""Generate, save, and load simulated Continuous DiD panel data."""

import logging

import pandas as pd
from diff_diff import generate_continuous_did_data

from utils import get_project_root

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROJECT_ROOT = get_project_root()
SIMULATED_PATH = PROJECT_ROOT / "data" / "simulated" / "continuous_did_simulated.csv"

# Simulation parameters (kept explicit for reproducibility)
N_UNITS = 1000
N_PERIODS = 8
COHORT_PERIODS = [3, 5]
NEVER_TREATED_FRAC = 0.3
ATT_FUNCTION = "linear"
ATT_INTERCEPT = 1.0
ATT_SLOPE = 2.0
SEED = 42


def generate_simulated_data() -> pd.DataFrame:
    """Generate synthetic Continuous DiD panel data."""
    return generate_continuous_did_data(
        n_units=N_UNITS,
        n_periods=N_PERIODS,
        cohort_periods=COHORT_PERIODS,
        never_treated_frac=NEVER_TREATED_FRAC,
        att_function=ATT_FUNCTION,
        att_intercept=ATT_INTERCEPT,
        att_slope=ATT_SLOPE,
        seed=SEED,
    )


def save_simulated_data(data: pd.DataFrame) -> None:
    """Save simulated dataset to CSV, creating the directory if needed."""
    SIMULATED_PATH.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(SIMULATED_PATH, index=False)
    logger.info("Saved data to: %s", SIMULATED_PATH)


def load_simulated_data() -> pd.DataFrame:
    """Load saved simulated dataset."""
    return pd.read_csv(SIMULATED_PATH)


if __name__ == "__main__":
    df = generate_simulated_data()
    save_simulated_data(df)
    



"""Load Vaghul-Zipperer state minimum wage data and build the dose/first_treat
columns, then join to QCEW county employment data (downloaded separately from
https://www.bls.gov/cew/downloadable-data-files.htm - not directly fetchable
from this environment, no BLS network access here).

Dose = the dollar gap between a state's own minimum wage and the federal
minimum in the year it first sets an independent minimum. This is fixed at
onset (not an evolving stock like broadband was) and is a real dollar figure,
not a privacy-bucketed code - no artificial ceiling on dose richness.
"""

import logging

import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MW_ANNUAL_PATH = "data/real/mw_state_annual.xlsx"
MW_PANEL_OUTPUT_PATH = "data/real/minwage_panel.csv"


def load_minwage_panel(path: str = MW_ANNUAL_PATH) -> pd.DataFrame:
    """Load the VZ annual state minimum wage file and build first_treat/dose.

    first_treat = first year the state's own minimum wage exceeds the federal
    minimum (state sets an independent floor). States that never do so are
    first_treat = 0 (never-treated).

    dose = the dollar gap (state minimum - federal minimum) in the first
    treated year - a one-time value fixed at onset, not a moving series.
    """
    df = pd.read_excel(path)
    df = df.rename(columns={
        "State FIPS Code": "fips",
        "Name": "state",
        "State Abbreviation": "state_abbr",
        "Year": "year",
        "Annual State Minimum": "state_mw",
        "Annual Federal Minimum": "federal_mw",
    })

    # Source xlsx stores these with float precision artifacts (e.g. 2.7999999...
    # instead of 2.80) - round before using them anywhere downstream.
    df["state_mw"] = df["state_mw"].round(2)
    df["federal_mw"] = df["federal_mw"].round(2)
    df["gap"] = (df["state_mw"] - df["federal_mw"]).round(2).clip(lower=0)

    onset_year = df[df["gap"] > 0].groupby("fips")["year"].min()
    onset_gap = df.merge(onset_year.rename("onset_year"), on="fips", how="left")
    onset_gap = onset_gap[onset_gap["year"] == onset_gap["onset_year"]][["fips", "gap"]]
    onset_gap = onset_gap.set_index("fips")["gap"]

    df = df.merge(onset_year.rename("first_treat"), on="fips", how="left")
    df["first_treat"] = df["first_treat"].fillna(0).astype(int)
    df["dose"] = df["fips"].map(onset_gap).fillna(0)

    # Convert first_treat=0 (never-treated) doses to 0 explicitly (already
    # NaN->0 via fillna above, but keep this line for clarity/auditability)
    df.loc[df["first_treat"] == 0, "dose"] = 0

    return df[["fips", "state", "state_abbr", "year", "state_mw", "federal_mw",
               "gap", "first_treat", "dose"]]


def load_qcew_county_annual(path: str, naics_prefix: str = "722") -> pd.DataFrame:
    """Load a QCEW county annual singlefile and filter to one industry.

    QCEW's standard annual singlefile columns include: area_fips, own_code,
    industry_code, agglvl_code, year, annual_avg_emplvl, avg_annual_pay,
    total_annual_wages. NAICS 722 (food services) is the standard low-wage
    sector used in the minimum wage literature (Cengiz et al., Card).

    Adjust naics_prefix and the agglvl_code filter to match whatever QCEW
    file vintage you actually download - column names have been stable for
    years but confirm against the file you get before trusting this as-is.
    """
    df = pd.read_csv(path, dtype={"area_fips": str, "industry_code": str})

    df = df[df["industry_code"].str.startswith(naics_prefix)]
    df = df[df["own_code"] == 5]  # 5 = private ownership, standard for this literature

    df["state_fips"] = df["area_fips"].str[:2].astype(int)

    return df[["area_fips", "state_fips", "year", "annual_avg_emplvl", "avg_annual_pay"]]


def build_panel(minwage_path: str, qcew_path: str, naics_prefix: str = "722") -> pd.DataFrame:
    """Join the state-level minimum wage panel to county-level QCEW employment."""
    mw = load_minwage_panel(minwage_path)
    qcew = load_qcew_county_annual(qcew_path, naics_prefix=naics_prefix)

    panel = qcew.merge(
        mw, left_on=["state_fips", "year"], right_on=["fips", "year"], how="left"
    )

    return panel


def save_panel(df: pd.DataFrame, path: str = MW_PANEL_OUTPUT_PATH) -> None:
    """Save a panel (minimum-wage-only or joined with QCEW) to CSV."""
    df.to_csv(path, index=False)
    logger.info("Saved data to: %s", path)


if __name__ == "__main__":
    # Minimum-wage-only panel for now - swap in build_panel(...) once you
    # have a QCEW file downloaded and want the joined version instead.
    mw_panel = load_minwage_panel()
    save_panel(mw_panel)
    