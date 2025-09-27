from datetime import date
import sys, pathlib
root = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))

from underwriter.engine import build_monthly_cf, _add_income_ops
from underwriter.schema import Assumptions

# Minimal assumptions for smoke test
assump = Assumptions(
    purchase_price=1_000_000,
    closing_costs=20000,
    date_of_close=date(2024,4,15),
    property_sf=10000,
    gross_potential_rent_per_sf_per_year=10.0,
    total_other_income_per_sf_per_year=1.0,
    operating_expenses_per_sf_per_year=3.0,
    total_capital_improvements=120000,
    capital_improvement_start_month=2,
    capital_improvement_end_month=5,
    capital_reserve_per_sf_per_year=0.5,
    hold_period_months=36,
    exit_cap_rate=0.06,
    cost_of_sale_percentage=0.025,
    ltv=0.7,
    loan_origination_fee=0.01,
    interest_rate=0.045,
    amortization_years=30
)

df = build_monthly_cf(assump)
df = _add_income_ops(df, assump)
print(df.head(8).to_string())
print('\nSum CapitalImprovements:', df['CapitalImprovements'].sum())
