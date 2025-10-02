import sys, pathlib
from pathlib import Path
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

import json as _json
from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops, build_equity_cashflows, build_cashoncash_table
from underwriter import metrics as m

scenario = Path("scenarios") / "sample_assumptions.json"
if not scenario.exists():
    print("Scenario file not found:", scenario)
    raise SystemExit(1)

with scenario.open('r', encoding='utf-8') as fh:
    data = _json.load(fh)

assump = Assumptions.model_validate(data)

df = build_monthly_cf(assump)
df = _add_income_ops(df, assump)
eq = build_equity_cashflows(assump, df)
coc_tbl = build_cashoncash_table(assump, df, eq)

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

out_dir = Path('outputs')
out_dir.mkdir(parents=True, exist_ok=True)
with (out_dir / 'metrics.json').open('w', encoding='utf-8') as fh:
    _json.dump(out, fh, indent=2, default=str)

print("Wrote metrics to", out_dir / 'metrics.json')

# Also write equity schedule and cash-on-cash tables for review
eq_path = out_dir / 'equity_schedule.csv'
coc_path = out_dir / 'cash_on_cash.csv'
eq.to_csv(eq_path, index=True)
coc_tbl.to_csv(coc_path, index=True)
print("Wrote", eq_path)
print("Wrote", coc_path)
