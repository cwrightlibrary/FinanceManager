"""
This module includes models for a financial profile.

The script isn't meant to be run on its own, the `Profile` and
DebtRepaymentProfile` classes are the main classes to import for
functionality.
"""

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
        account_type (Literal["Checking", "Saving"]): Checking or
            saving account
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
    Models a monthly bill with the ability to randomize the amount.

    Attributes:
        name (str): The entity billing the user
        bill_type (BillType): Categorization for the bill
        randomize (bool): Whether to use a randomly generated range or a
            set price
        amount (Optional[Decimal]): _The fixed final amount for the bill
        amount_range (Optional[tuple[Decimal, Decimal]]): The range
            used for generating a random amount
    """
    name: str
    bill_type: BillType
    randomize: bool = False
    amount: Optional[Decimal] = Field(default=None, ge=0, decimal_places=2)
    amount_range: Optional[tuple[Decimal, Decimal]] = None

    @model_validator(mode="after")
    def set_amount(self) -> Self:
        """
        Assigns the `amount` if `randomize` is `True` and `amount_range`
        is not empty.

        Raises:
            ValueError: `amount_range` or `amount` must be populated

        Returns:
            Self: A `Bill` object
        """
        if self.randomize and self.amount_range and not self.amount:
            low, high = self.amount_range
            val = random.uniform(float(low), float(high))
            self.amount = Decimal(str(val)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        elif not self.amount_range and not self.amount:
            raise ValueError("Must set amount_range or amount")

        return self

    def generate_random_amount(self) -> Decimal:
        """
        Generates a random range between the low and high values in the `amount_range`.

        Returns:
            Decimal: The new `amount` value generated from the range
        """
        amount = Decimal("0.00")
        if self.randomize and self.amount_range:
            low, high = map(float, self.amount_range)
            amount += Decimal(str(round(random.uniform(low, high), 2)))
        elif self.amount:
            amount += self.amount

        return amount


class Debt(BaseModel):
    """
    Models debt behavior with details for accurately calculating
    interest.

    Attributes:
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
        """_Applies interest using `amount` and `apr` values._
        """
        self.amount *= 1 + self.apr / 12


class Income(BaseModel):
    """
    Creates an income-stream using **bi-weekly** payment from
    employement. The monthly income is a computed property.

    Attributes:
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
        return round(monthly_pay, 2)


class TaxSystem(BaseModel):
    """
    Calculates income taxes and capital gains taxes based on income
    brackets and capital gains rate.
    """
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

    def income_tax(self, annual_income: Decimal) -> Decimal:
        """
        Calculates income tax based off of an annual income amount.

        Args:
            annual_income (Decimal): The annual income in USD

        Returns:
            Decimal: The income tax amount in USD
        """
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

    def capital_gains_tax(self, gains: Decimal) -> Decimal:
        """
        Calculates capital gains tax based off of an annual income
        amount.

        Args:
            gains (Decimal): The gains in USD

        Returns:
            Decimal: The capital gains tax in USD
        """
        return gains * self.capital_gains_rate


class Profile(BaseModel):
    """
    A full financial profile model for users to populate.

    Attributes:
        name (str): The name of the profile, _e.g., Karl Marx, Karl,_
            or _Marx_.
        start_date (datetime): The date this profile was created
        current_date (datetime): **Not for use by users**, keeps this
            time up to date for comparison
        bank_accounts (list[BankAccount]): A list of all accounts of
            type _Checking_ or _Saving_
        debts (list[Debt]): A list of all of the debt belonging to the
            user and their profile
        income (list[Income]): A list of income streams, primarily used
            for income in relation to employment
        bills (list[Bill]): A list of the user's monthly bills
        tax_system (TaxSystem): Not really for the user to configure
        capital_gains (Decimal): _Yet to be implemented_
        debt_repayment (bool): Whether or not this account should be
            used for calculating loan payment plans
    """

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
        """Returns the sum of all bank accounts in the profile."""
        return sum((a.amount for a in self.bank_accounts), Decimal("0"))

    def monthly_income(self) -> Decimal:
        """Returns the sum of all monthly incomes."""
        return sum((i.monthly_amount for i in self.income), Decimal("0"))

    def monthly_bills(self) -> Decimal:
        """Returns the sum of all of the monthly bills."""
        amount = Decimal("0.00")
        for bill in self.bills:
            amount += bill.generate_random_amount()

        return amount

    def total_debt(self) -> Decimal:
        """Returns the sum of the monthly debt."""
        return sum((i.amount for i in self.debts), Decimal("0"))

    def inflate(self, inflation_rate: Decimal) -> None:
        """Used for simulation and simulating an inflation rate upon
        all income and bills in the profile."""
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
        """Calculates and returns the total tax for the year."""
        inc_tax = self.tax_system.income_tax(self.monthly_income())
        cap_tax = self.tax_system.capital_gains_tax(self.capital_gains)

        return inc_tax + cap_tax


class DebtRepaymentProfile(Profile):
    """
    A subclass `Profile` for calculating loan payment plans.

    Attributes:
        payment_style (str): As of now, the only style to use is an
            avalanche method of loan forgiveness (which is yet to be
            implemented)
        highest_apr_amount (Decimal): Set an alternate minimum for the
            loan with the highest APR
        last_debt_amount (Decimal): Set an alternate minimum for the
            last loan in `debts`
        logs (list[dict]): A log of the profile history, used for
            historical purposes
        rent (Decimal): The `Bill` in the profile of type _rent_
    """
    payment_style: str = "Avalanche"

    highest_apr_amount: Decimal = Field(default=Decimal("0"), ge=0)
    last_debt_amount: Decimal = Field(default=Decimal("0"), ge=0)

    logs: list[dict] = Field(default_factory=list)
    rent: Decimal = Decimal("0")

    def snapshot_month(self) -> dict:
        """Returns a model dump of the current state of the profile."""
        return self.model_dump(exclude={"logs"})

    def model_post_init(self, context: Any) -> None:
        """Sets the `rent` attribute automatically."""
        self.logs.append(self.snapshot_month())
        for bill in self.bills:
            if bill.bill_type == "Rent" and bill.amount:
                self.rent = bill.amount

    def simulate_month(self) -> None:
        """WIP function to simulate a month. Will add more
        functionality."""
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
        """
        A simulation to pay off all loans with customized minimums.

        Args:
            avalanche (bool, optional): Loan payment strategy. Defaults
                to True.

        Returns:
            tuple[str, int]: A markdown table of monthly payments and
                the total months to completely pay off debt
        """
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

            monthly_payments = {debt.name: Decimal(
                "0.00") for debt in debts_to_pay}

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
                                highest_apr_amount -
                                monthly_payments[debt.name],
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
                len(debts_to_pay) >= 2
                and debts_to_pay[-2].amount <= 0
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
