"""Load and combine NCES CCD School District Finance Survey (F-33) files
across years into one long panel. Source: LRS replication package's
ccdfinance folder (originally NCES's own F-33 survey).

Column names shift slightly across survey vintages, but LEAID, FIPST,
TOTALEXP, and V33 (enrollment) are confirmed present and consistent from
1990 through 2013 - V33 is used rather than the newer MEMBERSCH alias
(which only appears in later-vintage files) specifically because it's the
one enrollment field present in every year, including the earliest (1990).

Missing years in the LRS package as of this writing: 1991, 1993, 1994.
The 2012 file (sdf121a_suppressed) has NCES privacy suppression applied -
check separately for how much of it is usable before trusting that year.
"""

import pandas as pd
from pathlib import Path

# All raw CCD/Census finance files live here, not in src/ - keeps code and
# data separated the same way data/simulated/ and data/real/ already are.
FINANCE_DATA_DIR = Path("data/real/finance")

# Map each year to its file - all 21 available years from the LRS package
# (1991, 1993, 1994 are missing from the package entirely, not an error here)
FINANCE_FILES = {
    1990: FINANCE_DATA_DIR / "sdf901a.sas7bdat.gz",
    1992: FINANCE_DATA_DIR / "sdf921a.sas7bdat.gz",
    1995: FINANCE_DATA_DIR / "sdf95c1d.sas7bdat.gz",
    1996: FINANCE_DATA_DIR / "sdf96c1b.sas7bdat.gz",
    1997: FINANCE_DATA_DIR / "sdf97d1a.sas7bdat.gz",
    1998: FINANCE_DATA_DIR / "sdf98d1e.sas7bdat.gz",
    1999: FINANCE_DATA_DIR / "sdf991c.sas7bdat.gz",
    2000: FINANCE_DATA_DIR / "sdf001d.sas7bdat.gz",
    2001: FINANCE_DATA_DIR / "sdf011d.sas7bdat.gz",
    2002: FINANCE_DATA_DIR / "sdf021c.sas7bdat.gz",
    2003: FINANCE_DATA_DIR / "sdf031b.sas7bdat.gz",
    2004: FINANCE_DATA_DIR / "sdf041b.sas7bdat.gz",
    2005: FINANCE_DATA_DIR / "sdf051c.sas7bdat.gz",
    2006: FINANCE_DATA_DIR / "sdf061a.sas7bdat.gz",
    2007: FINANCE_DATA_DIR / "sdf071a.sas7bdat.gz",
    2008: FINANCE_DATA_DIR / "sdf081a.sas7bdat.gz",
    2009: FINANCE_DATA_DIR / "sdf091a.sas7bdat.gz",
    2010: FINANCE_DATA_DIR / "sdf101a_sas.sas7bdat.gz",
    2011: FINANCE_DATA_DIR / "sdf11_1a.sas7bdat.gz",
    2012: FINANCE_DATA_DIR / "sdf121a_suppressed.sas7bdat.gz",  # "suppressed" in filename but verified
    # to have missingness in line with neighboring normal years (~9-10%) - safe to include
    2013: FINANCE_DATA_DIR / "sdf13_1a.sas7bdat.gz",
}


def load_one_year(path, year: int) -> pd.DataFrame:
    """Load a single year's F-33 file and extract the columns we need.

    Tries gzip decompression first (the files as downloaded from ICPSR are
    gzip-compressed even when the filename doesn't show a .gz suffix),
    falling back to a plain read if that fails.
    """
    try:
        df = pd.read_sas(path, compression="gzip")
    except Exception:
        df = pd.read_sas(path)

    df.columns = [c.upper() for c in df.columns]

    sub = df[["LEAID", "FIPST", "TOTALEXP", "V33"]].copy()
    sub = sub.rename(columns={"V33": "enrollment"})
    sub["year"] = year
    sub["LEAID"] = sub["LEAID"].astype(str)  # SAS files store this as bytes

    return sub


def build_finance_panel(files: dict = FINANCE_FILES) -> pd.DataFrame:
    """Combine all available years into one long district-level panel.

    Filters out NCES's missing-data sentinel codes (-1, -2, -9, etc.) by
    requiring enrollment and expenditure to both be strictly positive -
    those sentinels otherwise produce nonsense per-pupil figures (e.g. a
    -1/-1 division computing to 1.0, which looks like real data but isn't).
    """
    panels = [load_one_year(path, year) for year, path in files.items()]
    panel = pd.concat(panels, ignore_index=True)

    panel = panel[(panel["enrollment"] > 0) & (panel["TOTALEXP"] > 0)]
    panel["per_pupil_exp"] = panel["TOTALEXP"] / panel["enrollment"]

    return panel


# CCD's own school district survey has no 1993 or 1994 data (per LRS paper
# footnote 16: "Census data are available in 1989-90 and 1991-92, and
# annually since 1994-95"). LRS patched this gap using the Census Bureau's
# separate Annual Survey of Government Finances - Elementary-Secondary
# component (elsec93.txt / elsec94.txt) instead of interpolating. Same
# district-level resolution as CCD, but TOTALEXP is reported in THOUSANDS
# of dollars here, unlike the raw-dollar CCD .sas7bdat files - must be
# multiplied by 1000 before computing per-pupil spending, or results come
# out ~1000x too small.
GOV_FINANCE_FILES = {
    1993: FINANCE_DATA_DIR / "elsec93.txt.gz",
    1994: FINANCE_DATA_DIR / "elsec94.txt.gz",
}


def load_gov_finance_year(path, year: int) -> pd.DataFrame:
    """Load one year of the Census Annual Survey of Government Finances
    (Elementary-Secondary component) and scale to match the CCD panel."""
    try:
        df = pd.read_csv(path, compression="gzip")
    except Exception:
        df = pd.read_csv(path)
    df.columns = [c.strip() for c in df.columns]

    sub = df[["FIPS", "STATE", "TOTALEXP", "V33"]].copy()
    sub["TOTALEXP"] = sub["TOTALEXP"] * 1000  # thousands -> raw dollars, matches CCD scale
    sub = sub.rename(columns={"V33": "enrollment", "FIPS": "LEAID", "STATE": "FIPST"})
    sub["year"] = year
    sub["LEAID"] = sub["LEAID"].astype(str)  # match CCD's string-typed LEAID

    return sub


def build_full_finance_panel(
    ccd_files: dict = FINANCE_FILES, gov_files: dict = GOV_FINANCE_FILES
) -> pd.DataFrame:
    """Combine CCD years with the two Census government-finance gap years
    into one continuous 1990-2013 panel (still missing 1991 - CCD itself
    has no data for that year and LRS's own footnote does not mention a
    substitute for it either)."""
    ccd_panel = build_finance_panel(ccd_files)

    gov_panels = [load_gov_finance_year(path, year) for year, path in gov_files.items()]
    gov_panel = pd.concat(gov_panels, ignore_index=True)
    gov_panel = gov_panel[(gov_panel["enrollment"] > 0) & (gov_panel["TOTALEXP"] > 0)]
    gov_panel["per_pupil_exp"] = gov_panel["TOTALEXP"] / gov_panel["enrollment"]

    return pd.concat([ccd_panel, gov_panel], ignore_index=True).sort_values(
        ["LEAID", "year"]
    ).reset_index(drop=True)