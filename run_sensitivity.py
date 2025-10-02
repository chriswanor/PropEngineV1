import sys, pathlib
from pathlib import Path
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

import json as _json
import pandas as pd
from underwriter.schema import Assumptions
from underwriter.sensitivity import run_sensitivity_grid, summarize_sensitivity

scenario = Path("scenarios") / "sample_assumptions.json"
if not scenario.exists():
    print("Scenario file not found:", scenario)
    raise SystemExit(1)

with scenario.open('r', encoding='utf-8') as fh:
    data = _json.load(fh)

assump = Assumptions.model_validate(data)

sens_df = run_sensitivity_grid(assump)
sum_df = summarize_sensitivity(sens_df)

out_dir = Path('outputs')
out_dir.mkdir(parents=True, exist_ok=True)

sens_path = out_dir / 'sensitivity_grid.csv'
sum_path = out_dir / 'sensitivity_summary.csv'

sens_df.to_csv(sens_path, index=False)
sum_df.to_csv(sum_path, index=False)

print("Wrote", sens_path)
print("Wrote", sum_path)

