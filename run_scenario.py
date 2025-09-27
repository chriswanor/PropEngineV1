import sys, pathlib
from pathlib import Path
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

import json
from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops

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

out_dir = Path('outputs')
out_dir.mkdir(parents=True, exist_ok=True)
out_file = out_dir / 'schedule.csv'
df.to_csv(out_file, index=True)
print('\nWrote schedule to', out_file)
print('\nHead:')
print(df.head().to_string())
