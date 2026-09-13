"""Quick check: does the F-33 file actually contain TLOCREV (local revenue)?"""

import glob
import pandas as pd

finance_path = r"C:\Users\HP\Documents\continuous_DiD\data\f33_finance"

txt_files = glob.glob(finance_path + r"\**\*.txt", recursive=True)
print(f"Found {len(txt_files)} F-33 txt files")

# Just check the first one -- column layout is consistent across years
if txt_files:
    sample = txt_files[0]
    print(f"\nChecking: {sample}")
    df = pd.read_csv(sample, sep="\t", encoding="latin1", low_memory=False, nrows=5)
    df.columns = df.columns.str.strip()
    print(f"\nFULL column list ({len(df.columns)} columns):")
    for col in df.columns:
        print(" -", col)

    # Flag anything revenue-related
    print("\nColumns containing 'REV' (revenue-related):")
    for col in df.columns:
        if "REV" in col.upper():
            print(" -", col)

    # Flag anything local-related
    print("\nColumns containing 'LOC' (local-related):")
    for col in df.columns:
        if "LOC" in col.upper():
            print(" -", col)