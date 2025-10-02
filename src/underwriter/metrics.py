import pandas as pd
import numpy as np
import numpy_financial as npf
import xirr
import numpy_financial as npf
import scipy.optimize as opt
from underwriter.schema import Assumptions
from underwriter.engine import build_monthly_cf, _add_income_ops, build_equity_cashflows, build_cashoncash_table

def going_in__cap_rate(df: pd.DataFrame, a: Assumptions) -> float:
    noi = df.iloc[0:12]["NetOperatingIncome"].sum()
    cap = noi / a.purchase_price
    return cap

def loan_constant(a: Assumptions, df: pd.DataFrame) -> float: 
    loan_amount = a.purchase_price * a.ltv
    total_debt_service = df.iloc[0:12]["PrincipalPayment"].sum() + df.iloc[0:12]["InterestPayment"].sum()
    return total_debt_service / loan_amount

def going_in_dscr(a: Assumptions, df: pd.DataFrame) -> float: 
    noi = df.iloc[0:12]["NetOperatingIncome"].sum()
    total_debt_service = df.iloc[0:12]["PrincipalPayment"].sum() + df.iloc[0:12]["InterestPayment"].sum()
    return noi / total_debt_service

def going_in_debt_yield(a: Assumptions, df: pd.DataFrame) -> float:
    loan_amount = a.purchase_price * a.ltv
    noi = df.iloc[0:12]["NetOperatingIncome"].sum()
    return noi / loan_amount

def exit_ltv(a: Assumptions, eq: pd.DataFrame) -> float:
    s_proceeds = eq["SaleProceeds"].sum()
    loan_payoff = eq["LoanPayoff"].sum()
    return loan_payoff / s_proceeds if s_proceeds != 0 and loan_payoff != 0 else np.nan

# -----------------------------
# Robust XIRR fallback via root finding
# -----------------------------

def _xirr_fallback(cashflows: dict) -> float | None:
    if not cashflows or len(cashflows) < 2:
        return None
    # Sort by date and convert to year fractions from t0
    items = sorted(cashflows.items(), key=lambda kv: kv[0])
    t0 = items[0][0]

    def days_frac(d):
        try:
            delta_days = (d - t0).days
        except Exception:
            # If pandas Timestamp, convert to python datetime
            delta_days = (getattr(d, 'to_pydatetime', lambda: d)() - getattr(t0, 'to_pydatetime', lambda: t0)()).days
        return delta_days / 365.0

    ts = np.array([days_frac(d) for d, _ in items], dtype=float)
    cfs = np.array([float(v) for _, v in items], dtype=float)

    # Require both signs
    if not (np.any(cfs > 0) and np.any(cfs < 0)):
        return None

    def npv(r):
        return np.sum(cfs / np.power(1.0 + r, ts))

    # Scan for a bracket with sign change
    grid = [-0.95, -0.75, -0.5, -0.3, -0.2, -0.1, -0.05, -0.01,
            0.0, 0.01, 0.03, 0.05, 0.08, 0.10, 0.15, 0.2, 0.3, 0.5,
            1.0, 2.0, 3.0, 5.0, 10.0]
    vals = [npv(r) for r in grid]
    for i in range(len(grid) - 1):
        a_r, b_r = grid[i], grid[i + 1]
        fa, fb = vals[i], vals[i + 1]
        if not np.isfinite(fa) or not np.isfinite(fb):
            continue
        if fa == 0:
            return a_r
        if fa * fb < 0:
            try:
                root = opt.brentq(npv, a_r, b_r, maxiter=200, xtol=1e-10)
                return float(root)
            except Exception:
                continue
    return None

def unlevered_irr(eq: pd.DataFrame) -> float:
    series = eq["UnleveredCashFlow"]
    # Build date->value mapping, filter zeros/NaNs
    lib = {}
    for ts, val in series.items():
        try:
            fv = float(val)
        except Exception:
            continue
        if not np.isfinite(fv) or fv == 0:
            continue
        try:
            d = ts.date()  # pandas.Timestamp
        except AttributeError:
            d = ts          # datetime.date
        lib[d] = fv

    # Primary: true XIRR
    try:
        res = xirr.xirr(lib)
        if res is not None:
            return res
    except Exception:
        pass

    # Fallback 1: root-finding over dated cashflows
    fb = _xirr_fallback(lib)
    if fb is not None:
        return fb

    # Fallback 2: regular IRR on ordered cashflows, annualized from monthly
    try:
        ordered = series.loc[sorted(series.index)].astype(float).values
        irr_m = npf.irr(ordered)
        if irr_m is None or not np.isfinite(irr_m):
            return None
        return (1.0 + irr_m) ** 12 - 1.0
    except Exception:
        return None

def levered_irr(eq: pd.DataFrame) -> float:
    series = eq["LeveredCashFlow"]
    # Build date->value mapping, filter zeros/NaNs
    lib = {}
    for ts, val in series.items():
        try:
            fv = float(val)
        except Exception:
            continue
        if not np.isfinite(fv) or fv == 0:
            continue
        try:
            d = ts.date()  # pandas.Timestamp
        except AttributeError:
            d = ts          # datetime.date
        lib[d] = fv

    # Primary: true XIRR
    try:
        res = xirr.xirr(lib)
        if res is not None:
            return res
    except Exception:
        pass

    # Fallback 1: root-finding over dated cashflows
    fb = _xirr_fallback(lib)
    if fb is not None:
        return fb

    # Fallback 2: regular IRR on ordered cashflows, annualized from monthly
    try:
        ordered = series.loc[sorted(series.index)].astype(float).values
        irr_m = npf.irr(ordered)
        if irr_m is None or not np.isfinite(irr_m):
            return None
        return (1.0 + irr_m) ** 12 - 1.0
    except Exception:
        return None

def unlevered_equity_multiple(eq: pd.DataFrame) -> float:
    total_invested = eq["UnleveredCashFlow"].loc[eq["UnleveredCashFlow"] < 0].sum()
    total_returned = eq["UnleveredCashFlow"].loc[eq["UnleveredCashFlow"] > 0].sum()
    return total_returned / abs(total_invested) if total_invested != 0 else 0

def levered_equity_multiple(eq: pd.DataFrame) -> float:
    total_invested = eq["LeveredCashFlow"].loc[eq["LeveredCashFlow"] < 0].sum()
    total_returned = eq["LeveredCashFlow"].loc[eq["LeveredCashFlow"] > 0].sum()
    return total_returned / abs(total_invested) if total_invested != 0 else 0

def avg_unlevered_coc(coc_tbl: pd.DataFrame, a: Assumptions) -> float:
    effectivehold = a.hold_period_months if a.hold_period_months <= len(coc_tbl) else len(coc_tbl)
    # Match column name as created in build_cashoncash_table
    avg_ucoc = coc_tbl["UnleveredCashonCash"].iloc[0:effectivehold].mean()
    return avg_ucoc

def avg_levered_coc(coc_tbl: pd.DataFrame, a:Assumptions) -> float:
    effectivehold = a.hold_period_months if a.hold_period_months <= len(coc_tbl) else len(coc_tbl)
    # Match column name as created in build_cashoncash_table
    avg_lcoc = coc_tbl["LeveredCashonCash"].iloc[0:effectivehold].mean()
    return avg_lcoc

def year1_op_ex_ratio(df: pd.DataFrame) -> float:
    total_op_ex = df.iloc[0:12]["OperatingExpenses"].sum()
    total_egr = df.iloc[0:12]["EffectiveGrossRevenue"].sum()
    return total_op_ex / total_egr if total_egr != 0 else 0

