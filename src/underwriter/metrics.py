import pandas as pd
import numpy as np
import numpy_financial as npf

from underwriter.schema import Assumptions
from underwriter.engine import build__monthly_cf, _add_income_ops, build_equity_cashflows, build_cashoncash_table

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
    
def levered_irr(eq: pd.DataFrame) -> float: ...
def unlevered_equity_multiple(eq: pd.DataFrame) -> float: ...
def levered_equity_multiple(eq: pd.DataFrame) -> float: ...
def avg_unlevered_coc(coc_tbl: pd.DataFrame) -> float: ...
def avg_levered_coc(coc_tbl: pd.DataFrame) -> float: ...

# --- OPERATING ---
def year1_op_ex_ratio(df: pd.DataFrame) -> float: ...

