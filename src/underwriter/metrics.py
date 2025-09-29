import pandas as pd
import numpy as np
import numpy_financial as npf
import xirr
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

def unlevered_irr(eq: pd.DataFrame) -> float:
    series = eq["UnleveredCashFlow"]
    lib = {ts.date(): float(val) for ts, val in series.items() if val != 0}

    try:
        ul_xirr = xirr.xirr(lib)
    except Exception:
        ul_xirr = None

    return ul_xirr

def levered_irr(eq: pd.DataFrame) -> float:
    series = eq["LeveredCashFlow"]
    lib = {ts.date(): float(val) for ts, val in series.items() if val != 0}

    try:
        l_xirr = xirr.xirr(lib)
    except Exception:
        l_xirr = None

    return l_xirr

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
    avg_ucoc = coc_tbl["UnleveredCashOnCash"].iloc[0:effectivehold].mean()
    return avg_ucoc

def avg_levered_coc(coc_tbl: pd.DataFrame, a:Assumptions) -> float:
    effectivehold = a.hold_period_months if a.hold_period_months <= len(coc_tbl) else len(coc_tbl)
    avg_lcoc = coc_tbl["LeveredCashOnCash"].iloc[0:effectivehold].mean()
    return avg_lcoc

def year1_op_ex_ratio(df: pd.DataFrame) -> float:
    total_op_ex = df.iloc[0:12]["OperatingExpenses"].sum()
    total_egr = df.iloc[0:12]["EffectiveGrossRevenue"].sum()
    return total_op_ex / total_egr if total_egr != 0 else 0

