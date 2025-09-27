from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date

class Assumptions(BaseModel):

    # Purchase Metrics

    purchase_price: float = Field(..., gt = 0, description="Total asking acquisition price ($)")
    closing_costs: float = Field(..., ge = 0, description="Closing costs ($)")
    date_of_close: date = Field(..., description = "Acquisition Date (YYYY-MM-DD)")

    # Operating Metrics

    property_sf: float = Field(..., gt = 0, description="Total property square footage (SF)")
    gross_potential_rent_per_sf_per_year: float = Field(..., gt = 0, description="Gross potential rent per SF per year ($/SF/YR)")
    annual_rent_growth_rate: float = Field(0.04, ge = 0, le = 1, description="Annual rent growth rate (%)")
    general_vacancy_rate: float = Field(0.07, ge = 0, le = 1, description="General vacancy rate (%)")
    total_other_income_per_sf_per_year: float = Field(..., ge = 0, description="Total other income per SF per year ($/SF/YR)")
    annual_other_income_growth_rate: float = Field(0.03, ge = 0, le = 1, description="Annual other income growth rate (%)")
    operating_expenses_per_sf_per_year: float = Field(..., ge = 0, description="Operating expenses per SF per year ($/SF/YR)")
    annual_expense_growth_rate: float = Field(0.025, ge = 0, le = 1, description="Annual expense growth rate (%)")
    total_capital_improvements: float = Field(..., ge = 0, description="Total capital improvements ($)")
    capital_improvement_start_month: int = Field(..., description="Capital improvement start month (month)")
    capital_improvement_end_month: int = Field(..., description="Capital improvement end month (month)")
    capital_reserve_per_sf_per_year: float = Field(..., ge = 0, description="Capital reserve per SF per year ($/SF/YR)")
    capital_reserve_growth_rate: float = Field(0.02, ge = 0, le = 1, description="Capital reserve growth rate (%)")

    # sale metrics
    exit_cap_rate: float = Field(0.06, ge = 0, le = 1, description="Exit cap rate (%)")
    hold_period_months: int = Field(..., gt = 0, description="Hold period (months)")
    cost_of_sale_percentage: float = Field(0.025, ge = 0, le = 1, description="Cost of sale (%)")
    
    # financing metrics

    ltv: float = Field(0.7, ge = 0, le = 1, description="Loan to value (%)")
    loan_origination_fee: float = Field(0.01, ge = 0, le = 1, description="Loan origination fee (%)")
    interest_rate: float = Field(0.045, ge = 0, le = 1, description="Interest rate (%)")
    amortization_years: int = Field(30, gt = 0, description="Amortization period (years)")

