import sys, pathlib
from pathlib import Path
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

import json as _json
import os
import argparse

from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops, build_equity_cashflows
from underwriter import metrics as m
from underwriter.sensitivity import run_sensitivity_grid, summarize_sensitivity
from underwriter.ai import report_generator


def build_metrics(assump: Assumptions) -> dict:
    df = build_monthly_cf(assump)
    df = _add_income_ops(df, assump)
    eq = build_equity_cashflows(assump, df)

    out = {
        "going_in_cap_rate": m.going_in__cap_rate(df, assump),
        "loan_constant": m.loan_constant(assump, df),
        "going_in_dscr": m.going_in_dscr(assump, df),
        "going_in_debt_yield": m.going_in_debt_yield(assump, df),
        "exit_ltv": m.exit_ltv(assump, eq),
        "unlevered_irr": m.unlevered_irr(eq),
        "levered_irr": m.levered_irr(eq),
        "unlevered_em": m.unlevered_equity_multiple(eq),
        "levered_em": m.levered_equity_multiple(eq),
    }
    return out


def build_sensitivity_summary(assump: Assumptions) -> dict:
    sens_df = run_sensitivity_grid(assump)
    sum_df = summarize_sensitivity(sens_df)
    # Convert a small selection to dict to keep prompt concise
    summary = sum_df.head(10).to_dict(orient="records") if hasattr(sum_df, 'to_dict') else {}
    return {"summary_rows": summary}


def main():
    parser = argparse.ArgumentParser(description="Generate AI investment report from sample assumptions")
    parser.add_argument("--api-key", dest="api_key", default=os.getenv("OPENAI_API_KEY"), help="OpenAI API key (falls back to OPENAI_API_KEY env var)")
    parser.add_argument("--offline", action="store_true", help="Generate a deterministic test report without calling OpenAI")
    args = parser.parse_args()
    scenario = Path("scenarios") / "sample_assumptions.json"
    if not scenario.exists():
        print("Scenario file not found:", scenario)
        raise SystemExit(1)

    with scenario.open('r', encoding='utf-8') as fh:
        data = _json.load(fh)

    assump = Assumptions.model_validate(data)

    metrics = build_metrics(assump)
    sensitivity = build_sensitivity_summary(assump)

    if args.offline:
        # Produce a simple, deterministic test report
        report_lines = [
            "Executive Summary:",
            f"- Levered IRR: {metrics.get('levered_irr')}",
            f"- Unlevered IRR: {metrics.get('unlevered_irr')}",
            f"- Going-in DSCR: {metrics.get('going_in_dscr')}",
            "",
            "Market Benchmark Analysis:",
            f"- Cap Rate: {metrics.get('going_in__cap_rate') if 'going_in__cap_rate' in metrics else metrics.get('going_in_cap_rate')}",
            f"- Loan Constant: {metrics.get('loan_constant')}",
            "",
            "Sensitivity Insights:",
            f"- Summary rows: {len(sensitivity.get('summary_rows', []))}",
            "",
            "Final Recommendation:",
            "- BUY (test report)",
        ]
        report = "\n".join(report_lines)
    else:
        try:
            report = report_generator.generate_ai_report(metrics, sensitivity, api_key=args.api_key)
        except Exception as e:
            print("❌ Failed to generate AI report:", str(e))
            print("Hint: set OPENAI_API_KEY environment variable or pass --api-key.")
            raise

    out_dir = Path('outputs')
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / 'ai_report.txt'
    with out_path.open('w', encoding='utf-8') as fh:
        fh.write(report)

    print("\n=== AI Report (saved to outputs/ai_report.txt) ===\n")
    print(report)


if __name__ == "__main__":
    main()


