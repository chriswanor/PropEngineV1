import sys, pathlib
from pathlib import Path
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

import json
from underwriter.schema import Assumptions
from underwriter.engine import (
    build_monthly_cf,
    _add_income_ops,
    build_equity_cashflows,
    build_cashoncash_table,
)

scenario = Path("scenarios") / "sample_assumptions.json"
if not scenario.exists():
    print("Scenario file not found:", scenario)
    raise SystemExit(1)

import json as _json
with scenario.open('r', encoding='utf-8') as fh:
    data = _json.load(fh)

# validate using pydantic v2 API (model_validate)
assump = Assumptions.model_validate(data)
print('Loaded assumptions:')
print(_json.dumps(assump.model_dump(), indent=2, default=str))

df = build_monthly_cf(assump)
df = _add_income_ops(df, assump)

# Build equity schedule (levered and unlevered) and cash-on-cash table
eq = build_equity_cashflows(assump, df)
coc = build_cashoncash_table(assump, df, eq)

# Merge equity rows (Date index) into main schedule (month-end index)
# We align on dates; where columns don't exist, fill with 0
df_full = df.copy()
for col in [
    "PurchasePrice","ClosingCosts","SaleProceeds","CostOfSale",
    "UnleveredCashFlow","LoanProceeds","LoanOriginationFee",
    "LoanPayoff","LeveredCashFlow",
]:
    df_full[col] = 0.0

common = df_full.index.intersection(eq.index)
if not common.empty:
    for col in eq.columns:
        df_full.loc[common, col] = eq.loc[common, col]

# Optionally, add Year-level cash-on-cash lookups back onto month rows
df_full["UnleveredCashonCash"] = np.nan
df_full["LeveredCashonCash"] = np.nan
if hasattr(coc, 'index') and not coc.empty:
    # map YearNum to CoC values
    year_to_ucoc = coc["UnleveredCashonCash"].to_dict()
    year_to_lcoc = coc["LeveredCashonCash"].to_dict()
    df_full["UnleveredCashonCash"] = df_full["YearNum"].map(year_to_ucoc)
    df_full["LeveredCashonCash"] = df_full["YearNum"].map(year_to_lcoc)

out_dir = Path('outputs')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'schedule.csv'
df_full.to_csv(out_file, index=True)
print('\nWrote schedule to', out_file)
print('\nHead:')
print(df.head().to_string())
