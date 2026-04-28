import copy
import random

from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal, ROUND_HALF_UP
from prettytable import PrettyTable, MARKDOWN
from pydantic import BaseModel, Field, model_validator, computed_field
from typing import Any, Literal, Optional, Self


class BankAccount(BaseModel):
    """
    This just simply models a bank account with account type and funds.

    Args:
        name (str): The bank or provider
        account_type (Literal["Checking", "Saving"]): Checking or saving account
        amount (Decimal): How much money is in the account
    """

    name: str
    account_type: Literal["Checking", "Saving"]
    amount: Decimal = Field(ge=0, decimal_places=2)


BillType = Literal[
    "Internet",
    "Utilities",
    "Groceries",
    "Phones",
    "Games",
    "Music",
    "Entertainment",
    "Daycare",
    "Rent",
    "Extra spending",
]


class Bill(BaseModel):
    """
    Models a monthly bill with the ability to randomize the amount with a range of values.

    Args:
        name (str): The entity billing the user
        bill_type (BillType): Categorization for the bill
        randomize (bool): Either a randomly generated range or set price
        amount (Optional[Decimal]): For setting a final amount
        amount_range (Optional[tuple[Decimal, Decimal]]): For generating a random amount
    """

    name: str
    bill_type: BillType
    randomize: bool = False
    amount: Optional[Decimal] = Field(ge=0, decimal_places=2)
    amount_range: Optional[tuple[Decimal, Decimal]] = None

    @model_validator(mode="after")
    def set_amount(self) -> Self:
        if self.randomize and self.amount_range and not self.amount:
            low, high = self.amount_range
            val = random.uniform(float(low), float(high))
            self.amount = Decimal(str(val)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        elif not self.amount_range and not self.amount:
            raise ValueError("Must set amount_range or amount")

        return self

    def change_amount_range(self, new_range: tuple[Decimal, Decimal]) -> None:
        if self.amount_range:
            self.amount_range = new_range

    def generate_random_amount(self) -> Decimal:
        amount = Decimal("0.00")
        if self.randomize and self.amount_range:
            low, high = map(float, self.amount_range)
            amount += Decimal(str(round(random.uniform(low, high), 2)))
        elif self.amount:
            amount += self.amount

        return amount


class Debt(BaseModel):
    """
    Models debt behavior with details for accurately calculating interest.

    Args:
        name (str): The debt provider
        amount (Decimal): The current, active balance
        apr (Decimal): Debt's APR (e.g. `0.075`)
        min (Decimal): The minimum monthly payment
    """

    name: str
    amount: Decimal = Field(ge=0, decimal_places=2)
    apr: Decimal = Field(ge=0, decimal_places=4)
    min: Decimal = Field(ge=0, decimal_places=2)

    def apply_interest(self):
        self.amount *= 1 + self.apr / 12


class Income(BaseModel):
    """
    Creates an income-stream using **bi-weekly** payment from employement.

    Args:
        income_name (str): Preferably the employer
        amount (Decimal): How much money is coming in **bi-weekly**
    """

    income_name: str
    amount: Decimal = Field(ge=0, decimal_places=2)

    @computed_field
    @property
    def monthly_amount(self) -> Decimal:
        annual_salary = self.amount * 26
        monthly_pay = annual_salary / 12
        return monthly_pay


class TaxSystem(BaseModel):
    brackets: list[tuple[Decimal, Decimal]] = Field(
        default=[
            (Decimal("0"), Decimal("0.10")),
            (Decimal("11600"), Decimal("0.12")),
            (Decimal("47150"), Decimal("0.22")),
            (Decimal("100525"), Decimal("0.24")),
            (Decimal("191950"), Decimal("0.32")),
        ]
    )

    capital_gains_rate: Decimal = Decimal("0.15")

    def income_tax(self, annual_income: Decimal):
        tax = Decimal("0")
        prev = Decimal("0")

        for threshold, rate in self.brackets:
            taxable = max(
                Decimal("0"), min(annual_income - threshold, threshold - prev)
            )
            tax += taxable * rate
            prev = threshold

        tax += max(Decimal("0"), annual_income - prev) * self.brackets[-1][1]
        return tax

    def capital_gains_tax(self, gains: Decimal):
        return gains * self.capital_gains_rate


class Profile(BaseModel):
    """A full financial object for a user."""

    name: str
    start_date: datetime = Field(default_factory=datetime.today)
    current_date: datetime = Field(default_factory=datetime.today)

    bank_accounts: list[BankAccount]
    debts: list[Debt]
    income: list[Income]
    bills: list[Bill]

    tax_system: TaxSystem = Field(default_factory=TaxSystem)
    capital_gains: Decimal = Field(default=Decimal("0"), ge=0)

    debt_repayment: bool = False

    def total_accounts(self) -> Decimal:
        return sum((a.amount for a in self.bank_accounts), Decimal("0"))

    def monthly_income(self) -> Decimal:
        return sum((i.monthly_amount for i in self.income), Decimal("0"))

    def monthly_bills(self) -> Decimal:
        amount = Decimal("0.00")
        for bill in self.bills:
            amount += bill.generate_random_amount()

        return amount

    def total_debt(self) -> Decimal:
        return sum((i.amount for i in self.debts), Decimal("0"))

    def inflate(self, inflation_rate: Decimal) -> None:
        factor = 1 + inflation_rate

        for income in self.income:
            income.amount *= factor

        for bill in self.bills:
            if bill.amount:
                bill.amount *= factor
            elif bill.amount_range:
                for range in bill.amount_range:
                    range *= factor

    @computed_field
    @property
    def total_tax(self) -> Decimal:
        inc_tax = self.tax_system.income_tax(self.monthly_income())
        cap_tax = self.tax_system.capital_gains_tax(self.capital_gains)

        return inc_tax + cap_tax


class DebtRepaymentProfile(Profile):
    payment_style: str = "Avalanche"

    highest_apr_amount: Decimal = Field(default=Decimal("0"), ge=0)
    last_debt_amount: Decimal = Field(default=Decimal("0"), ge=0)

    logs: list[dict] = Field(default_factory=list)
    rent: Decimal = Decimal("0")

    def snapshot_month(self) -> dict:
        return self.model_dump(exclude={"logs"})

    def model_post_init(self, context: Any) -> None:
        self.logs.append(self.snapshot_month())
        for bill in self.bills:
            if bill.bill_type == "Rent" and bill.amount:
                self.rent = bill.amount

    def simulate_month(self) -> None:
        self.current_date += relativedelta(months=1)

        checking_account = next(
            (acc for acc in self.bank_accounts if acc.account_type == "Checking"), None
        )

        available_funds = self.monthly_income() - self.monthly_bills()

        is_avalanche = self.payment_style.lower() == "avalanche"
        self.debts.sort(
            key=lambda debt: debt.apr if is_avalanche else debt.amount,
            reverse=is_avalanche,
        )

        if self.highest_apr_amount > 0 and self.debts:
            self.debts[0].min = self.highest_apr_amount

        for debt in self.debts:
            debt.apply_interest()

            if debt.amount > 0:
                payment = min(debt.amount, debt.min)
                debt.amount -= payment
                available_funds -= payment

        if self.debts:
            target_debt = self.debts[0]
            if (
                available_funds > 0
                and self.highest_apr_amount > 0
                and target_debt.amount > 0
            ):
                extra_payment = min(
                    target_debt.amount, self.highest_apr_amount - target_debt.min
                )
                target_debt.amount -= extra_payment
                available_funds -= extra_payment

        if self.debts:
            all_others_paid = all(debt.amount <= 0 for debt in self.debts[:-1])
            last_debt = self.debts[-1]

            if all_others_paid and last_debt.amount > 0 and self.last_debt_amount > 0:
                last_debt.min = self.last_debt_amount

        if checking_account:
            checking_account.amount += available_funds

        self.logs.append(self.snapshot_month())

    def simulate_loan_evisceration(
        self,
        avalanche: bool = True,
    ) -> tuple[str, int]:
        highest_apr_loan = float(self.highest_apr_amount)

        debts_to_pay = copy.deepcopy(self.debts)

        if avalanche:
            debts_to_pay.sort(key=lambda debt: debt.apr, reverse=True)
        else:
            debts_to_pay.sort(key=lambda debt: debt.amount)

        if highest_apr_loan > debts_to_pay[0].min and debts_to_pay:
            debts_to_pay[0].min = Decimal(str(highest_apr_loan))

        total_months = 0

        previous_total_balance = sum(d.amount for d in debts_to_pay)

        debt_headers = [
            "Date",
            "Account",
            "Payment",
            "Balance After",
            "Monthly Cash Left",
        ]

        pt = PrettyTable(debt_headers)

        _today = datetime.today()
        start_date = datetime(_today.year, _today.month, 1)

        while any(debt.amount > 0 for debt in debts_to_pay):
            current_year, current_month = divmod(total_months, 12)

            month_val = (start_date.month + current_month - 1) % 12 + 1
            year_val = (
                start_date.year
                + current_year
                + (start_date.month + current_month - 1) // 12
            )

            current_date = datetime(year_val, month_val, 1)
            date_display = current_date.strftime("%B %Y")

            income_total = self.monthly_income()
            bills_total = self.monthly_bills()
            available_funds = income_total - bills_total

            monthly_payments = {debt.name: Decimal("0.00") for debt in debts_to_pay}

            for debt in debts_to_pay:
                debt.apply_interest()

            for debt in debts_to_pay:
                if debt.amount > 0:
                    payment = min(debt.amount, debt.min)
                    debt.amount -= payment
                    available_funds -= payment
                    monthly_payments[debt.name] = payment

            if available_funds > 0 and highest_apr_loan > 0:
                highest_apr_amount = Decimal(str(highest_apr_loan))
                for debt_idx, debt in enumerate(debts_to_pay):
                    if debt_idx != len(debts_to_pay) - 1:
                        if debt.amount > 0:
                            potential_extra = max(
                                Decimal("0"),
                                highest_apr_amount - monthly_payments[debt.name],
                            )
                            extra_pay = min(
                                debt.amount, available_funds, potential_extra
                            )

                            debt.amount -= extra_pay
                            available_funds -= extra_pay
                            monthly_payments[debt.name] += extra_pay

                            if available_funds <= 0:
                                break

            if (
                debts_to_pay[0].amount <= 0
                and debts_to_pay[-1].amount > 0
                and self.last_debt_amount > debts_to_pay[-1].min
            ):
                debts_to_pay[-1].min = Decimal(str(self.last_debt_amount))

            active_debts = [
                d
                for d in debts_to_pay
                if d.amount > 0 or monthly_payments.get(d.name, 0) > 0
            ]

            for idx, debt in enumerate(active_debts):
                pay_amt = monthly_payments.get(debt.name, 0)
                row_date = date_display if idx == 0 else ""

                pt.add_row(
                    [
                        row_date,
                        debt.name,
                        f"${pay_amt:,.2f}",
                        f"${debt.amount:,.2f}",
                        f"${available_funds:,.2f}",
                    ]
                )

            current_total_balance = sum(d.amount for d in debts_to_pay)
            if current_total_balance >= previous_total_balance and total_months > 0:
                return "Error: Debt is growing faster than payments.", total_months

            previous_total_balance = current_total_balance
            total_months += 1

            if total_months > 1200:
                break

        pt.set_style(MARKDOWN)
        return pt.get_string(), total_months
