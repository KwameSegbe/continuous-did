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