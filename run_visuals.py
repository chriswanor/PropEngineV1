import sys, pathlib
from pathlib import Path
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

import json as _json
from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops, build_equity_cashflows, build_cashoncash_table
from underwriter.visuals import create_visual_report

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
coc = build_cashoncash_table(assump, df, eq)

create_visual_report(assump, df, eq, coc)
print("Report generated.")

