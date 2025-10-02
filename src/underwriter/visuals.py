import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.backends.backend_pdf import PdfPages

from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops, build_equity_cashflows, build_cashoncash_table
from underwriter.metrics import (
    going_in__cap_rate,
    loan_constant,
    going_in_dscr,
    going_in_debt_yield,
    exit_ltv,
    unlevered_irr,
    levered_irr,
    unlevered_equity_multiple,
    levered_equity_multiple,
    avg_unlevered_coc,
    avg_levered_coc,
    year1_op_ex_ratio,
)
from underwriter.sensitivity import run_sensitivity_grid, summarize_sensitivity

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "report.pdf")


def create_visual_report(a: Assumptions, df_full: pd.DataFrame, eq: pd.DataFrame, coc_tbl: pd.DataFrame):
    """Generate a multi-page PDF report with cash flow visuals, metrics, and sensitivity."""

    with PdfPages(OUTPUT_FILE) as pdf:

        # -----------------------------
        # Cash Flow Graph
        # -----------------------------
        plt.figure(figsize=(10, 6))
        df_full[["CashFlowBeforeDebtService", "CashFlowAfterDebtService"]].plot(ax=plt.gca())
        plt.title("Monthly Cash Flows")
        plt.ylabel("Cash Flow ($)")
        plt.xlabel("Date")
        plt.grid(True)
        pdf.savefig()
        plt.close()

        # -----------------------------
        # Cash-on-Cash Graph
        # -----------------------------
        plt.figure(figsize=(10, 6))
        coc_tbl.plot(ax=plt.gca(), marker="o")
        plt.title("Annual Cash-on-Cash Returns")
        plt.ylabel("Return (%)")
        plt.xlabel("Year")
        plt.grid(True)
        pdf.savefig()
        plt.close()

        # -----------------------------
        # Return Metrics Summary Table
        # -----------------------------
        metrics = {
            "Going-in Cap Rate": going_in__cap_rate(df_full, a),
            "Loan Constant": loan_constant(a, df_full),
            "Going-in DSCR": going_in_dscr(a, df_full),
            "Going-in Debt Yield": going_in_debt_yield(a, df_full),
            "Exit LTV": exit_ltv(a, eq),
            "Unlevered IRR": unlevered_irr(eq),
            "Levered IRR": levered_irr(eq),
            "Unlevered Equity Multiple": unlevered_equity_multiple(eq),
            "Levered Equity Multiple": levered_equity_multiple(eq),
            "Avg Unlevered CoC": avg_unlevered_coc(coc_tbl, a),
            "Avg Levered CoC": avg_levered_coc(coc_tbl, a),
            "Year 1 OpEx Ratio": year1_op_ex_ratio(df_full),
        }

        metrics_df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])

        plt.figure(figsize=(8, len(metrics_df) * 0.4 + 1))
        plt.axis("off")
        table = plt.table(
            cellText=metrics_df.values,
            colLabels=metrics_df.columns,
            loc="center",
            cellLoc="left",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1.2, 1.2)
        plt.title("Return Metrics Summary", pad=20)
        pdf.savefig()
        plt.close()

        # -----------------------------
        # Sensitivity Tornado Chart (Levered IRR range as impact)
        # -----------------------------
        sens_grid = run_sensitivity_grid(a)
        # Compute range of IRR for Levered only to build tornado
        levered = sens_grid[sens_grid["Type"] == "Levered"]
        irr_ranges = (
            levered.groupby("Assumption")["IRR"].agg(lambda s: (s.max() - s.min()))
            .sort_values()
        )
        tornado = pd.DataFrame({
            "Assumption": irr_ranges.index,
            "Impact": irr_ranges.values * 100.0,  # percentage points
        })

        plt.figure(figsize=(10, 6))
        plt.barh(tornado["Assumption"], tornado["Impact"], color="steelblue")
        plt.title("Sensitivity Analysis (Levered IRR range)")
        plt.xlabel("Impact (percentage points)")
        plt.ylabel("Assumption")
        plt.grid(axis="x")
        pdf.savefig()
        plt.close()

    print(f"✅ Report generated at: {OUTPUT_FILE}")