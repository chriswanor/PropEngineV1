import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
from underwriter.schema import Assumptions

def build_monthly_cf(a: Assumptions) -> pd.DataFrame:

    # Month index: use month-end one month after closing
    # Example: close 2021-03-31 -> first period end 2021-04-30
    first_period_end = a.date_of_close + relativedelta(months=+1, day=31)
    idx = pd.date_range(start=pd.Timestamp(first_period_end), periods=a.hold_period_months + 12, freq='M')

    # month counter for formulas (n starts at 1)

    month = pd.Series(np.arange(1, len(idx) + 1, dtype = int), index = idx, name = "Month")
    year = pd.Series(np.ceil(month/12).astype(int), index = idx, name = "Year")

    df = pd.DataFrame(index = idx)
    df["MonthNum"]  = month
    df["YearNum"] = year
    df["YearsFrac"] = (month-1)/12
    df["YearsFloor"] = np.floor((month-1)/12)

    return df

def _add_income_ops(df: pd.DataFrame, a: Assumptions) -> pd.DataFrame:
    rent_base = a.property_sf * a.gross_potential_rent_per_sf_per_year/12
    other_income_base = a.property_sf * a.total_other_income_per_sf_per_year/12
    opex_base = a.property_sf * a.operating_expenses_per_sf_per_year/12
    capres_base = a.property_sf * a.capital_reserve_per_sf_per_year/12

    df["GrossPotentialRent"] = rent_base * (1 + a.annual_rent_growth_rate) ** df["YearsFrac"]
    df["GeneralVacancy"] = - df["GrossPotentialRent"] * a.general_vacancy_rate
   
    df["NetRentalRevenue"] = df["GrossPotentialRent"] + df["GeneralVacancy"]

    df["OtherIncome"] = other_income_base * (1 + a.annual_other_income_growth_rate) ** df["YearsFrac"]

    df["EffectiveGrossRevenue"] = df["NetRentalRevenue"] + df["OtherIncome"]

    df["OperatingExpenses"] = - opex_base * (1 + a.annual_expense_growth_rate) ** df["YearsFrac"]
   
    df["NetOperatingIncome"] = df["EffectiveGrossRevenue"] + df["OperatingExpenses"]
   
    df["CapitalReserve"] = - capres_base * (1 + a.capital_reserve_growth_rate) ** df["YearsFloor"]
    
    df["CapitalImprovements"] = 0.0

    # Safely extract start/end months from assumptions (they may be missing)
    cis = int(getattr(a, "capital_improvement_start_month", 1))
    cie = int(getattr(a, "capital_improvement_end_month", 0))

    # Clamp to valid MonthNum range (MonthNum starts at 1)
    cis = max(cis, 1)
    cie = min(cie, int(a.hold_period_months))

    # this section here needs to be revisted for further understand the logic
    cap_total = float(a.total_capital_improvements)
    if cap_total > 0 and cie >= cis:
        duration = cie - cis + 1
        monthly = cap_total / duration
        # what is the function of mask
        mask = (df["MonthNum"] >= cis) & (df["MonthNum"] <= cie)
        # how does the function loc work
        df.loc[mask, "CapitalImprovements"] = - monthly

    df["CashFlowBeforeDebtService"] = df["NetOperatingIncome"] + df["CapitalReserve"] + df["CapitalImprovements"]

    per  = df["MonthNum"].to_numpy()
    nper = int(a.amortization_years * 12)
    rate = a.interest_rate / 12.0
    pv   = a.purchase_price * a.ltv

    ip = npf.ipmt(rate, per, nper, pv)          # negative
    pp = npf.ppmt(rate, per, nper, pv)          # negative
    ip = np.where(per <= nper, ip, 0.0)
    pp = np.where(per <= nper, pp, 0.0)

    df["InterestPayment"]  = ip
    df["PrincipalPayment"] = pp
    df["CashFlowAfterDebtService"] = df["CashFlowBeforeDebtService"] + ip + pp

    # Month 1: Net rent should equal GPR * (1 - vacancy)
    m1 = df.iloc[0]
    print("Net check m1:",
        round(m1["NetRentalRevenue"], 2),
        round(m1["GrossPotentialRent"] * (1 - a.general_vacancy_rate), 2))

    # Debt service should be roughly constant (fixed-rate, fully amortizing)
    ds = df[["InterestPayment","PrincipalPayment"]].assign(DebtService=(df["InterestPayment"] + df["PrincipalPayment"]))
    print(ds.head(3))

    return df
    
def build_equity_cashflows(a:Assumptions, df_full: pd.DataFrame) -> pd.DataFrame:
    ops = df_full.iloc[:a.hold_period_months].copy()

    f12_noi = df_full["NetOperatingIncome"].iloc[a.hold_period_months : a.hold_period_months + 12].sum()
    sale_price_f12 = f12_noi / a.exit_cap_rate

    sale_price = sale_price_f12

    sale_costs = sale_price * a.cost_of_sale_percentage

    loan_amount = a.purchase_price * a.ltv
    loan_origin_fee = loan_amount * a.loan_origination_fee

    principal_paid = -ops["PrincipalPayment"].sum()
    loan_payoff_exit = max(loan_amount - principal_paid, 0)

    eq_index = [a.date_of_close] + ops.index.tolist()
    eq = pd.DataFrame(index = pd.Index(eq_index, name = "Date"))

    eq["PurchasePrice"] = 0.0 
    eq["ClosingCosts"] = 0.0
    eq["SaleProceeds"] = 0.0
    eq["CostOfSale"] = 0.0
    eq["UnleveredCashFlow"] = 0.0
    eq["LoanProceeds"] = 0.0
    eq["LoanOriginationFee"] = 0.0
    eq["LoanPayoff"] = 0.0
    eq["LeveredCashFlow"] = 0.0

    eq.iloc[0, eq.columns.get_loc("PurchasePrice")] = -a.purchase_price
    eq.iloc[0, eq.columns.get_loc("ClosingCosts")] = -a.closing_costs
    eq.iloc[0, eq.columns.get_loc("LoanProceeds")] = loan_amount
    eq.iloc[0, eq.columns.get_loc("LoanOriginationFee")] = -loan_origin_fee

    eq.iloc[0, eq.columns.get_loc("UnleveredCashFlow")] = eq.iloc[0]["PurchasePrice"] + eq.iloc[0]["ClosingCosts"]
    eq.iloc[0, eq.columns.get_loc("LeveredCashFlow")] = eq.iloc[0]["UnleveredCashFlow"] + eq.iloc[0]["LoanProceeds"] + eq.iloc[0]["LoanOriginationFee"]

    eq.iloc[1:, eq.columns.get_loc("UnleveredCashFlow")] = ops["CashFlowBeforeDebtService"].values
    eq.iloc[1:, eq.columns.get_loc("LeveredCashFlow")] = ops["CashFlowAfterDebtService"].values

    eq.iloc[-1, eq.columns.get_loc("UnleveredCashFlow")] += sale_price - sale_costs
    eq.iloc[-1, eq.columns.get_loc("LeveredCashFlow")] += sale_price - sale_costs - loan_payoff_exit

    eq.iloc[-1, eq.columns.get_loc("SaleProceeds")] = sale_price
    eq.iloc[-1, eq.columns.get_loc("CostOfSale")] = -sale_costs
    eq.iloc[-1, eq.columns.get_loc("LoanPayoff")] = -loan_payoff_exit

    return eq


def build_cashoncash_table(a:Assumptions, df_full: pd.DataFrame, eq: pd.DataFrame) -> pd.DataFrame:

    acq = pd.Timestamp(a.date_of_close)
    idx = pd.DatetimeIndex([acq] + list(df_full.index), name = "Date")
    cols = [
        "YearNum",
        "CashFlowBeforeDebtService",
        "CashFlowAfterDebtService",
        "UnleveredCashFlow",
        "LeveredCashFlow",
    ]

    tbl = pd.DataFrame(index = idx, columns = cols)

    tbl[:] = 0

    tbl.at[acq, "YearNum"] = 0

    common_df = df_full.index.intersection(tbl.index)
    if not common_df.empty:
        tbl.loc[common_df, "YearNum"] = df_full.loc[common_df, "YearNum"]
        tbl.loc[common_df, "CashFlowBeforeDebtService"] = df_full.loc[common_df, "CashFlowBeforeDebtService"]
        tbl.loc[common_df, "CashFlowAfterDebtService"] = df_full.loc[common_df, "CashFlowAfterDebtService"]

    common_eq = eq.index.intersection(tbl.index)
    if not common_eq.empty:
        tbl.loc[common_eq, "UnleveredCashFlow"] = eq.loc[common_eq, "UnleveredCashFlow"]
        tbl.loc[common_eq, "LeveredCashFlow"] = eq.loc[common_eq, "LeveredCashFlow"]


    hold_years = int(a.hold_period_months / 12)
    coc_cols = ["UnleveredCashonCash", "LeveredCashonCash"]

    coc_index = pd.Index(np.arange(0, hold_years + 1), name = "Year")
    coc_tbl = pd.DataFrame(index = coc_index, columns = coc_cols, dtype = float)
    coc_tbl[:] = np.nan

    unlevered_cost = a.purchase_price + a.closing_costs
    levered_cost = (unlevered_cost - a.purchase_price * a.ltv + a.purchase_price * a.ltv * a.loan_origination_fee)

    for i in range(1, hold_years + 1):
        c_mask = tbl["YearNum"] == i
        unlevered_cf = tbl.loc[c_mask, "UnleveredCashFlow"].sum()
        levered_cf = tbl.loc[c_mask, "LeveredCashFlow"].sum()
        coc_tbl.at[i, "UnleveredCashonCash"] = unlevered_cf / unlevered_cost if unlevered_cost != 0 else np.nan
        coc_tbl.at[i, "LeveredCashonCash"] = levered_cf / levered_cost if levered_cost != 0 else np.nan

    return coc_tbl


















    






  
   





