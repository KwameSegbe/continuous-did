"""Parallel trends identification for the Continuous DiD project.

Tests standard parallel trends (PT), which is what identifies ATT(d|d) -
the dose-response curve that is the headline result of this analysis.
Does NOT test strong parallel trends (SPT); pre-trend tests cannot
validate SPT since it involves treated potential outcomes.
"""

import logging

import matplotlib.pyplot as plt
import pandas as pd
from diff_diff.utils import check_parallel_trends_robust, equivalence_test_trends

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Equivalence margin for TOST: differences in pre-trends smaller than this
# are considered practically negligible. Tune to the outcome's scale.
EQUIVALENCE_MARGIN = 0.5
N_PERMUTATIONS = 999
SEED = 42


def plot_dose_trends(
    data: pd.DataFrame,
    outcome: str = "outcome",
    time: str = "period",
    dose: str = "dose",
    pre_periods: list[int] | None = None,
) -> None:
    """Plot mean outcome trends by dose group over time.

    Visual inspection is the first step: look for similar slopes across
    dose groups in pre-treatment periods, divergence only after treatment.
    """
    means = data.groupby([time, dose])[outcome].mean().unstack()

    fig, ax = plt.subplots(figsize=(9, 5))
    for d in means.columns:
        ax.plot(means.index, means[d], marker="o", label=f"Dose = {d}")

    if pre_periods:
        ax.axvline(
            x=max(pre_periods) + 0.5,
            color="gray",
            linestyle="--",
            label="Treatment starts",
        )

    ax.set_xlabel("Period")
    ax.set_ylabel(f"Mean {outcome}")
    ax.set_title("Outcome Trends by Dose Group")
    ax.legend()
    plt.tight_layout()
    plt.show()


def run_equivalence_test(
    data: pd.DataFrame,
    outcome: str = "outcome",
    time: str = "period",
    treatment_group: str = "treated",
    unit: str = "unit",
    pre_periods: list[int] | None = None,
    equivalence_margin: float = EQUIVALENCE_MARGIN,
) -> dict:
    """Run TOST equivalence test on pre-treatment trends.

    Answers: can we confirm the trend difference is smaller than a
    practically meaningful threshold? This is the primary evidence for
    PT, since it's more informative than a simple non-significant p-value.
    """
    results = equivalence_test_trends(
        data,
        outcome=outcome,
        time=time,
        treatment_group=treatment_group,
        unit=unit,
        pre_periods=pre_periods,
        equivalence_margin=equivalence_margin,
    )

    logger.info("TOST Equivalence Test")
    logger.info("Mean difference: %.4f", results["mean_difference"])
    logger.info("TOST p-value: %.4f", results["tost_p_value"])
    logger.info("Trends equivalent (alpha=0.05): %s", results["equivalent"])

    return results


def run_robust_test(
    data: pd.DataFrame,
    outcome: str = "outcome",
    time: str = "period",
    treatment_group: str = "treated",
    unit: str = "unit",
    pre_periods: list[int] | None = None,
    n_permutations: int = N_PERMUTATIONS,
    seed: int = SEED,
) -> dict:
    """Run Wasserstein-distance-based robust parallel trends test.

    Compares full distributions of outcome changes, not just means -
    a useful secondary check for continuous/dose treatments where
    mean-based tests can miss distributional differences across doses.
    """
    results = check_parallel_trends_robust(
        data,
        outcome=outcome,
        time=time,
        treatment_group=treatment_group,
        unit=unit,
        pre_periods=pre_periods,
        n_permutations=n_permutations,
        seed=seed,
    )

    logger.info("Robust (Wasserstein) Parallel Trends Test")
    logger.info("Wasserstein distance: %.4f", results["wasserstein_distance"])
    logger.info("Wasserstein p-value: %.4f", results["wasserstein_p_value"])
    logger.info("Parallel trends plausible: %s", results["parallel_trends_plausible"])

    return results


def run_parallel_trends_suite(
    data: pd.DataFrame,
    outcome: str = "outcome",
    time: str = "period",
    treatment_group: str = "treated",
    unit: str = "unit",
    dose: str = "dose",
    pre_periods: list[int] | None = None,
) -> dict:
    """Run the full PT identification suite: visual + TOST + Wasserstein.

    Returns a dict of all results for downstream reporting. This suite
    validates standard parallel trends (PT), which identifies ATT(d|d) -
    the dose-response curve. It does not, and cannot, validate strong
    parallel trends (SPT), which would be needed for ACRT comparisons
    across dose groups.
    """
    plot_dose_trends(data, outcome=outcome, time=time, dose=dose, pre_periods=pre_periods)

    equiv_results = run_equivalence_test(
        data,
        outcome=outcome,
        time=time,
        treatment_group=treatment_group,
        unit=unit,
        pre_periods=pre_periods,
    )

    robust_results = run_robust_test(
        data,
        outcome=outcome,
        time=time,
        treatment_group=treatment_group,
        unit=unit,
        pre_periods=pre_periods,
    )

    return {
        "equivalence": equiv_results,
        "robust": robust_results,
    }