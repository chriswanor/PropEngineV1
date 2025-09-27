import pandas as pd
import numpy as np
import numpy_financial as npf
import matplotlib.pyplot as plt
from dateutil.relativedelta import relativedelta
from underwriter.schema import Assumptions

def build_monthly_cf(a: Assumptions) -> pd.DataFrame:

    # month index: first full month after closing elngth = hold_period_months

    first_month = (a.date_of_close + relativedelta(months=+1)).replace(day=1)
    idx = pd.date_range(start=first_month, periods = a.hold_period_months + 12, freq = 'MS' )

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
    

    






  
   





