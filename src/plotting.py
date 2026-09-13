import requests
import os

# # Save location
# output_dir = r"C:\Users\HP\Documents\continuous_DiD\data\ospi_graduation"

# os.makedirs(output_dir, exist_ok=True)

# # Replace/add IDs as you discover older years
# datasets = {
#     "2014_15": "d5dm-bwe8",
#     "2016_17": "ef3e-qpb8",
#     "2017_18": "384s-ygbu",
#     "2018_19": "6iji-4nux",
#     "2019_20": "gges-4vcv",
#     "2020_21": "rrud-rd4u",
#     "2021_22": "i23g-ymbg",
#     "2022_23": "kigx-4b2d",
#     "2023_24": "76iv-8ed4",
#     "2024_25": "isxb-523t"
# }

# for year, dataset_id in datasets.items():

#     url = f"https://data.wa.gov/resource/{dataset_id}.csv?$limit=500000"

#     print(f"Downloading {year}...")

#     response = requests.get(url)

#     if response.status_code == 200:

#         file_path = os.path.join(
#             output_dir,
#             f"graduation_{year}.csv"
#         )

#         with open(file_path, "wb") as f:
#             f.write(response.content)

#         print(f"Saved: {file_path}")

#     else:
#         print(f"Failed {year}: {response.status_code}")

# print("Finished.")





# import os
# import requests

# output_dir = r"C:\Users\HP\Documents\continuous_DiD\data\f33_finance"
# os.makedirs(output_dir, exist_ok=True)

# headers = {
#     "User-Agent": "Mozilla/5.0"
# }

# # Fiscal years needed
# years = {
#     "2010_11": "sdf11_1a.xlsx",
#     "2011_12": "sdf12_1a.xlsx",
#     "2012_13": "sdf13_1a.xlsx",
#     "2013_14": "sdf14_1a.xlsx",
#     "2014_15": "sdf15_1a.xlsx",
#     "2015_16": "sdf16_1a.xlsx",
#     "2016_17": "sdf17_1a.xlsx",
#     "2017_18": "sdf18_1a.xlsx",
#     "2018_19": "sdf19_1a.xlsx",
#     "2019_20": "sdf20_1a.xlsx",
#     "2020_21": "sdf21_1a.xlsx",
#     "2021_22": "sdf22_1a.xlsx",
#     "2022_23": "sdf23_1a.xlsx",
# }

# base_url = "https://nces.ed.gov/ccd/data/zip/"

# for label, filename in years.items():

#     url = base_url + filename.replace(".xlsx", ".zip")

#     print(f"Downloading F-33 {label}...")

#     r = requests.get(
#         url,
#         headers=headers
#     )

#     if r.status_code == 200:

#         path = os.path.join(
#             output_dir,
#             f"F33_{label}.zip"
#         )

#         with open(path, "wb") as f:
#             f.write(r.content)

#         print("Saved:", path)

#     else:
#         print(
#             "FAILED",
#             label,
#             r.status_code,
#             url
#         )

# print("Finished")



# import os
# import zipfile

# folder = r"C:\Users\HP\Documents\continuous_DiD\data\f33_finance"

# for file in os.listdir(folder):

#     if file.endswith(".zip"):

#         zip_path = os.path.join(folder, file)

#         extract_folder = os.path.join(
#             folder,
#             file.replace(".zip", "")
#         )

#         os.makedirs(
#             extract_folder,
#             exist_ok=True
#         )

#         print(f"Extracting {file}...")

#         with zipfile.ZipFile(zip_path, "r") as z:
#             z.extractall(extract_folder)

#         print("Done:", extract_folder)

# print("All ZIP files extracted.")

# import pandas as pd
# import os
# import glob


# # Paths
# finance_path = r"C:\Users\HP\Documents\continuous_DiD\data\f33_finance"
# graduation_path = r"C:\Users\HP\Documents\continuous_DiD\data\ospi_graduation"


# # -----------------------------
# # LOAD F33 FINANCE FILES
# # -----------------------------

# print("Loading F-33 files...")

# finance_files = glob.glob(
#     os.path.join(finance_path, "*.xlsx")
# )

# finance_list = []

# for file in finance_files:

#     print("Reading:", file)

#     df = pd.read_excel(file)

#     finance_list.append(df)


# finance = pd.concat(
#     finance_list,
#     ignore_index=True
# )


# print("Finance rows:", len(finance))


# # -----------------------------
# # CLEAN FINANCE
# # -----------------------------

# finance = finance[
#     finance["STABBR"] == "WA"
# ]


# finance = finance[
#     [
#         "LEAID",
#         "NAME",
#         "YEAR",
#         "MEMBERSCH",
#         "TCURELSC",
#         "TOTALREV",
#         "TOTALEXP"
#     ]
# ]


# finance["per_pupil_spending"] = (
#     finance["TCURELSC"]
#     /
#     finance["MEMBERSCH"]
# )


# # -----------------------------
# # LOAD OSPI GRADUATION
# # -----------------------------

# print("Loading OSPI graduation files...")


# graduation_files = glob.glob(
#     os.path.join(graduation_path, "*.csv")
# )


# grad_list = []

# for file in graduation_files:

#     print("Reading:", file)

#     df = pd.read_csv(file)

#     grad_list.append(df)


# graduation = pd.concat(
#     grad_list,
#     ignore_index=True
# )


# print("Graduation rows:", len(graduation))


# # -----------------------------
# # CLEAN OSPI
# # -----------------------------

# graduation = graduation[
#     graduation["organizationlevel"]
#     == "District"
# ]


# graduation = graduation[
#     [
#         "districtorganizationid",
#         "districtname",
#         "schoolyear",
#         "graduationrate"
#     ]
# ]


# # Rename for merge

# graduation = graduation.rename(
#     columns={
#         "districtorganizationid":"LEAID",
#         "schoolyear":"YEAR"
#     }
# )


# # -----------------------------
# # MERGE
# # -----------------------------

# print("Merging datasets...")


# panel = finance.merge(
#     graduation,
#     on=["LEAID", "YEAR"],
#     how="inner"
# )


# print(panel.head())

# print(
#     "Final panel rows:",
#     len(panel)
# )


# # Save

# output = r"C:\Users\HP\Documents\continuous_DiD\data\real\WA_schoolfinance_graduation_panel.csv"

# os.makedirs(
#     os.path.dirname(output),
#     exist_ok=True
# )


# panel.to_csv(
#     output,
#     index=False
# )


# print("Saved:", output)





"""
Build WA school finance + graduation panel.

Pipeline:
1. Extract F-33 zip files (NCES finance data)
2. Load F-33 txt files -> finance dataframe
3. Clean finance data (WA only)
4. Load OSPI graduation csv files -> graduation dataframe
5. Clean graduation data
6. Merge on ID (districtorganizationid / districtcode) if possible
7. If ID merge fails, fall back to normalized-name matching
8. Save panel
"""

import os
import re
import glob
import zipfile
import difflib

import pandas as pd


# =====================================================
# PATHS
# =====================================================

finance_path = r"C:\Users\HP\Documents\continuous_DiD\data\f33_finance"
graduation_path = r"C:\Users\HP\Documents\continuous_DiD\data\ospi_graduation"
output_path = r"C:\Users\HP\Documents\continuous_DiD\data\real\WA_schoolfinance_graduation_panel.csv"


# =====================================================
# 1. EXTRACT F33 ZIP FILES
# =====================================================

print("Extracting F-33 ZIP files...")

for file in os.listdir(finance_path):
    if file.endswith(".zip"):
        zip_path = os.path.join(finance_path, file)
        extract_folder = os.path.join(finance_path, file.replace(".zip", ""))

        if not os.path.exists(extract_folder):
            os.makedirs(extract_folder, exist_ok=True)
            print("Extracting:", file)
            with zipfile.ZipFile(zip_path, "r") as z:
                z.extractall(extract_folder)

print("Extraction complete.")


# =====================================================
# 2. LOAD F33 TXT FILES
# =====================================================

print("\nLoading F-33 TXT files...")

txt_files = glob.glob(finance_path + r"\**\*.txt", recursive=True)

print("Files found:")
for f in txt_files:
    print(f)

finance_list = []

for file in txt_files:
    print("Reading:", file)
    try:
        df = pd.read_csv(file, sep="\t", encoding="latin1", low_memory=False)
        finance_list.append(df)
    except Exception as e:
        print("FAILED:", file, e)

if len(finance_list) == 0:
    raise Exception("No F33 files loaded")

finance = pd.concat(finance_list, ignore_index=True)

print("Finance rows:", len(finance))
print(finance.columns[:20])


# =====================================================
# 3. CLEAN FINANCE
# =====================================================

print("\nCleaning finance data...")

finance.columns = finance.columns.str.strip()

finance = finance[finance["STABBR"].astype(str).str.strip() == "WA"]

keep_cols = ["LEAID", "NAME", "YEAR", "MEMBERSCH", "TCURELSC", "TOTALREV", "TOTALEXP"]
finance = finance[keep_cols].copy()

finance["per_pupil_spending"] = (
    pd.to_numeric(finance["TCURELSC"], errors="coerce")
    / pd.to_numeric(finance["MEMBERSCH"], errors="coerce")
)

finance["YEAR"] = pd.to_numeric(finance["YEAR"], errors="coerce")
finance = finance.dropna(subset=["YEAR"])
finance["YEAR"] = finance["YEAR"].astype(int)

# F-33 YEAR is stored as 2-digit (13, 15, 16...) not 4-digit (2013, 2015...)
finance["YEAR"] = finance["YEAR"].apply(lambda y: 2000 + y if y < 100 else y)

finance["LEAID"] = (
    finance["LEAID"].astype(str).str.replace(".0", "", regex=False).str.strip().str.zfill(7)
)

print("WA Finance rows:", len(finance))


# =====================================================
# 4. LOAD OSPI GRADUATION DATA
# =====================================================

print("\nLoading OSPI graduation files...")

grad_files = glob.glob(graduation_path + r"\*.csv")

grad_list = []

for file in grad_files:
    print("Reading:", file)
    df = pd.read_csv(file, low_memory=False)
    grad_list.append(df)

graduation = pd.concat(grad_list, ignore_index=True)

print("Graduation rows:", len(graduation))
print(graduation.columns)


# =====================================================
# 5. CLEAN GRADUATION
# =====================================================

print("\nCleaning graduation data...")

graduation = graduation[graduation["organizationlevel"] == "District"].copy()

graduation = graduation[[
    "districtcode",
    "districtorganizationid",
    "districtname",
    "schoolyear",
    "graduationrate",
    "graduate",
    "finalcohort",
]]

graduation["YEAR"] = graduation["schoolyear"].astype(str).str[:4]
graduation["YEAR"] = pd.to_numeric(graduation["YEAR"], errors="coerce")
graduation = graduation.dropna(subset=["YEAR"])
graduation["YEAR"] = graduation["YEAR"].astype(int)

graduation["districtorganizationid"] = (
    graduation["districtorganizationid"].astype(str).str.replace(".0", "", regex=False).str.strip()
)
graduation["districtcode"] = (
    graduation["districtcode"].astype(str).str.replace(".0", "", regex=False).str.strip()
)

graduation_panel = (
    graduation
    .groupby(["districtorganizationid", "districtcode", "districtname", "YEAR"], as_index=False)
    .agg(
        graduationrate=("graduationrate", "mean"),
        graduate=("graduate", "sum"),
        finalcohort=("finalcohort", "sum"),
    )
)

print("Graduation panel rows:", len(graduation_panel))


# =====================================================
# 6. TRY ID-BASED MERGE
# =====================================================

print("\nFinance sample LEAIDs:", finance["LEAID"].head(10).tolist())
print("District Organization IDs:", graduation_panel["districtorganizationid"].head(10).tolist())
print("District Codes:", graduation_panel["districtcode"].head(10).tolist())

panel = finance.merge(
    graduation_panel,
    left_on=["LEAID", "YEAR"],
    right_on=["districtorganizationid", "YEAR"],
    how="inner",
)
print("\nRows after districtorganizationid merge:", len(panel))

if len(panel) == 0:
    panel = finance.merge(
        graduation_panel,
        left_on=["LEAID", "YEAR"],
        right_on=["districtcode", "YEAR"],
        how="inner",
    )
    print("Rows after districtcode merge:", len(panel))


# =====================================================
# 7. FALLBACK: NORMALIZED NAME MATCH
# =====================================================
# WA's districtcode/districtorganizationid are internal IDs, not NCES
# LEAIDs, so the ID merge above is expected to return 0 rows unless you
# have a crosswalk file. This fallback matches on cleaned district name
# instead, which works across virtually any state's CCD + state-agency
# data as long as naming is reasonably consistent.

def normalize_name(name: str) -> str:
    """Lowercase, strip common suffixes/punctuation so names compare cleanly."""
    if pd.isna(name):
        return ""
    n = str(name).lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)                     # drop punctuation
    n = re.sub(r"\bschool district\b", "", n)
    n = re.sub(r"\bschool dist\b", "", n)
    n = re.sub(r"\bpublic schools\b", "", n)
    n = re.sub(r"\bsd\b", "", n)
    n = re.sub(r"\bno\b", "", n)
    n = re.sub(r"\d+", "", n)                              # drop trailing district numbers
    n = re.sub(r"\s+", " ", n).strip()
    return n


if len(panel) == 0:
    print("\nID merge failed — falling back to name matching...")

    print("\n--- RAW NAME SAMPLES (before normalization) ---")
    print("Finance NAME sample:", finance["NAME"].dropna().unique()[:10].tolist())
    print("Graduation districtname sample:", graduation_panel["districtname"].dropna().unique()[:10].tolist())

    finance["name_key"] = finance["NAME"].apply(normalize_name)
    graduation_panel["name_key"] = graduation_panel["districtname"].apply(normalize_name)

    print("\n--- NORMALIZED NAME SAMPLES (after normalization) ---")
    print("Finance name_key sample:", finance["name_key"].dropna().unique()[:10].tolist())
    print("Graduation name_key sample:", graduation_panel["name_key"].dropna().unique()[:10].tolist())

    print("\nUnique finance name_keys:", finance["name_key"].nunique())
    print("Unique graduation name_keys:", graduation_panel["name_key"].nunique())
    overlap = set(finance["name_key"].unique()) & set(graduation_panel["name_key"].unique())
    print("Exact overlap count (any year):", len(overlap))
    print("Overlap sample:", list(overlap)[:10])

    print("\nFinance YEAR values:", sorted(finance["YEAR"].unique().tolist()))
    print("Graduation YEAR values:", sorted(graduation_panel["YEAR"].unique().tolist()))
    year_overlap = set(finance["YEAR"].unique()) & set(graduation_panel["YEAR"].unique())
    print("YEAR overlap:", sorted(year_overlap))
    if not year_overlap:
        print(">>> WARNING: no overlapping YEAR values at all — name match will be 0 no matter what. Check the offset above before going further.")

    # Exact match on normalized name first
    panel = finance.merge(
        graduation_panel,
        left_on=["name_key", "YEAR"],
        right_on=["name_key", "YEAR"],
        how="inner",
    )
    print("Rows after exact name_key merge:", len(panel))

    # For any finance districts that still didn't match, try fuzzy matching
    # against the unique set of graduation district names (once, not per-year).
    if len(panel) < finance["name_key"].nunique():
        matched_keys = set(panel["name_key"].unique()) if len(panel) else set()
        unmatched_keys = sorted(set(finance["name_key"].unique()) - matched_keys)
        grad_keys = graduation_panel["name_key"].unique().tolist()

        fuzzy_map = {}
        for key in unmatched_keys:
            if not key:
                continue
            best = difflib.get_close_matches(key, grad_keys, n=1, cutoff=0.85)
            if best:
                fuzzy_map[key] = best[0]

        print(f"\nFuzzy-matched {len(fuzzy_map)} additional district names:")
        for k, v in fuzzy_map.items():
            print(f"  '{k}'  ->  '{v}'")

        if fuzzy_map:
            finance["name_key_fuzzy"] = finance["name_key"].map(fuzzy_map).fillna(finance["name_key"])
            extra_panel = finance[finance["name_key"].isin(fuzzy_map.keys())].merge(
                graduation_panel,
                left_on=["name_key_fuzzy", "YEAR"],
                right_on=["name_key", "YEAR"],
                how="inner",
                suffixes=("", "_grad"),
            )
            panel = pd.concat([panel, extra_panel], ignore_index=True, sort=False)
            print("Rows after adding fuzzy matches:", len(panel))

    # Anything still unmatched — report it so you can add manual overrides
    still_unmatched = sorted(
        set(finance["name_key"].unique())
        - set(panel["name_key"].unique() if len(panel) else [])
    )
    if still_unmatched:
        print(f"\n{len(still_unmatched)} finance districts still unmatched. Examples:")
        for k in still_unmatched[:15]:
            print(" -", k)
        print("Add manual overrides to the `fuzzy_map` / a name-alias dict if needed.")


# =====================================================
# 8. SAVE
# =====================================================

print("\nFinal panel rows:", len(panel))
print(panel.head())

os.makedirs(os.path.dirname(output_path), exist_ok=True)
panel.to_csv(output_path, index=False)

print("\nSaved:", output_path)