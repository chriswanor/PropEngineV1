import pandas as pd
import numpy as np
from copy import deepcopy

from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops, build_equity_cashflows, build_cashoncash_table
from underwriter import metrics   # <-- where IRR, EM, CoC functions already live


# -----------------------------
# Global delta definitions
# -----------------------------

REL_DELTAS = np.arange(0.8, 1.25, 0.05)     # 80% → 120% in steps of 5%
ABS_DELTAS = [-0.02, -0.01, 0.01, 0.02]     # bumps for rates, cap rates, vacancy

# -----------------------------
# Assumption groups
# -----------------------------

ASSUMPTIONS_REL = [
    "closing_costs",
    "gross_potential_rent_per_sf_per_year",
    "total_other_income_per_sf_per_year",
    "operating_expenses_per_sf_per_year",
    "total_capital_improvements",
    "capital_reserve_per_sf_per_year",
    "cost_of_sale_percentage",
]

ASSUMPTIONS_ABS = [
    "annual_rent_growth_rate",
    "general_vacancy_rate",
    "annual_other_income_growth_rate",
    "annual_expense_growth_rate",
    "capital_reserve_growth_rate",
    "exit_cap_rate",
]

ASSUMPTIONS_SPECIAL = [
    "hold_period_months",   # scale in years
    "ltv",
    "loan_origination_fee",
    "interest_rate",
    "amortization_years",
]


# -----------------------------
# Helpers
# -----------------------------

def clone_with(a: Assumptions, field: str, new_val) -> Assumptions:
    """Return a deep copy of assumptions with one field changed."""
    a_new = deepcopy(a)
    setattr(a_new, field, new_val)
    return a_new


def eval_metrics(a: Assumptions) -> dict:
    """Build cashflows + compute return metrics for given assumptions."""
    # build cashflows
    df = build_monthly_cf(a)
    df = _add_income_ops(df, a)
    eq = build_equity_cashflows(a, df)
    coc_tbl = build_cashoncash_table(a, df, eq)

    # collect metrics
    return {
        "levered_irr": metrics.levered_irr(eq),
        "unlevered_irr": metrics.unlevered_irr(eq),
        "levered_em": metrics.levered_equity_multiple(eq),
        "unlevered_em": metrics.unlevered_equity_multiple(eq),
        "avg_levered_coc": metrics.avg_levered_coc(coc_tbl, a),
        "avg_unlevered_coc": metrics.avg_unlevered_coc(coc_tbl, a),
    }


# -----------------------------
# Main sensitivity function
# -----------------------------

def run_sensitivity_grid(a: Assumptions) -> pd.DataFrame:
    base = eval_metrics(a)  # baseline values
    rows = []

    # Relative multipliers
    for field in ASSUMPTIONS_REL:
        for mult in REL_DELTAS:
            new_val = getattr(a, field) * mult
            res = eval_metrics(clone_with(a, field, new_val))
            rows.append({
                "Assumption": field,
                "Delta": f"{mult:.2f}x",
                "Type": "Levered",
                "IRR": res["levered_irr"],
                "EM": res["levered_em"],
                "CoC": res["avg_levered_coc"],
            })
            rows.append({
                "Assumption": field,
                "Delta": f"{mult:.2f}x",
                "Type": "Unlevered",
                "IRR": res["unlevered_irr"],
                "EM": res["unlevered_em"],
                "CoC": res["avg_unlevered_coc"],
            })

    # Absolute bumps
    for field in ASSUMPTIONS_ABS:
        base_val = getattr(a, field)
        for bump in ABS_DELTAS:
            new_val = max(0, base_val + bump)
            res = eval_metrics(clone_with(a, field, new_val))
            rows.append({
                "Assumption": field,
                "Delta": f"{bump:+.2%}",   # e.g. "+1.00%" or "-2.00%"
                "Type": "Levered",
                "IRR": res["levered_irr"],
                "EM": res["levered_em"],
                "CoC": res["avg_levered_coc"],
            })
            rows.append({
                "Assumption": field,
                "Delta": f"{bump:+.2%}",
                "Type": "Unlevered",
                "IRR": res["unlevered_irr"],
                "EM": res["unlevered_em"],
                "CoC": res["avg_unlevered_coc"],
            })

    return pd.DataFrame(rows)

def summarize_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize sensitivity results by ranking assumptions
    from most sensitive to least for Levered and Unlevered.
    """
    rows = []
    metrics = ["IRR", "EM", "CoC"]

    for t in ["Levered", "Unlevered"]:
        df_t = df[df["Type"] == t]
        for field in df_t["Assumption"].unique():
            df_f = df_t[df_t["Assumption"] == field]
            row = {"Assumption": field, "Type": t}
            for m in metrics:
                rng = df_f[m].max() - df_f[m].min()
                row[f"{m}_Range"] = rng
            # Composite = average of ranges (normalize scale differences later if needed)
            row["CompositeRange"] = np.mean([row[f"{m}_Range"] for m in metrics])
            rows.append(row)

    summary = pd.DataFrame(rows)

    # Rank separately for Levered vs Unlevered
    ranked = summary.sort_values(["Type", "CompositeRange"], ascending=[True, False])
    return ranked.reset_index(drop=True)