import json
import pandas as pd
import streamlit as st

from decimal import Decimal
from enum import auto, Enum
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field
from typing import cast, Literal

from src.helpers.get_profile import GetProfile
from src.helpers.str_to_num import str_to_num

from src.models import (
    BankAccount,
    Bill,
    BillType,
    Debt,
    Income,
    Profile,
    DebtRepaymentProfile,
)


class AppMode(Enum):
    DASHBOARD = auto()
    SETUP_PROFILE = auto()
    DEBT_WIZARD = auto()
    OPTIONS = auto()


class AppState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    active_mode: AppMode = AppMode.DASHBOARD
    user_name: str = "Guest"
    debug_mode: bool = False
    run_count: int = Field(default=0, ge=0)


class PersonalFinances:
    def __init__(self):
        if "profile" not in st.session_state:
            st.session_state.profile = None

        if "state" not in st.session_state:
            st.session_state.state = AppState()

        if "accounts" not in st.session_state:
            st.session_state.accounts = []

        if "debts" not in st.session_state:
            st.session_state.debts = []

        if "incomes" not in st.session_state:
            st.session_state.incomes = []

        if "bills" not in st.session_state:
            st.session_state.bills = []

        if "run_count" not in st.session_state:
            st.session_state.run_count = 0

        self.profile: Profile | DebtRepaymentProfile | None = st.session_state.profile
        self.state: AppState = st.session_state.state
        self.accounts: list[BankAccount] = st.session_state.accounts
        self.debts: list[Debt] = st.session_state.debts
        self.incomes: list[Income] = st.session_state.incomes
        self.bills: list[Bill] = st.session_state.bills

        self.routes = {
            AppMode.DASHBOARD: self.render_dashboard,
            AppMode.SETUP_PROFILE: self.setup_profile,
            AppMode.DEBT_WIZARD: self.simulate,
            AppMode.OPTIONS: self.preferences,
        }

        self.get_profile = GetProfile()

        self.state.user_name = self.get_profile.name
        self.data = self.get_profile.data
        self.load_account()

        if self.state.user_name == "Guest" and st.session_state.run_count == 0:
            self.state.active_mode = AppMode.SETUP_PROFILE

        self.load_account()

    def start_app(self) -> None:
        dashboard_pg = st.Page(
            self.render_dashboard,
            title="Dashboard",
            icon="📊",
            default=(self.state.active_mode == AppMode.DASHBOARD),
        )

        profile_label = "Edit Profile" if self.profile else "Setup Profile"
        profile_icon = "✏️" if self.profile else "➕"
        profile_pg = st.Page(self.setup_profile, title=profile_label, icon=profile_icon)
        options_pg = st.Page(self.preferences, title="Preferences", icon="⚙️")

        wizard_pg = st.Page(self.simulate, title="Simulate", icon="💫")

        pages = {
            f"Welcome, {self.state.user_name}": [dashboard_pg, profile_pg, options_pg],
            "Debt Wizard": [wizard_pg],
        }

        pg = st.navigation(pages)

        pg.run()

    def preferences(self) -> None:
        st.title("⚙️ Preferences")
        upload_profile = st.file_uploader(
            "Replace profile", accept_multiple_files=False, type="json"
        )
        if upload_profile is not None:
            json_profile = json.load(upload_profile)
            with open(".user_profile.json", "w", encoding="utf-8") as f:
                json.dump(json_profile, f)
            st.rerun()

        self.state.debug_mode = st.toggle(
            "Enable Debug Mode",
            value=self.state.debug_mode,
        )

        if self.state.debug_mode:
            st.json(self.state.model_dump())

    def emit_event(self, mode: AppMode) -> None:
        self.state.active_mode = mode
        self.state.run_count += 1
        st.rerun()

    def render_sidebar(self) -> None:
        with st.sidebar:
            st.title(f"👋 Welcome, {self.state.user_name}")

            if self.state.user_name == "Guest":
                st.info("Please setup your profile")
            else:
                st.caption("Manage your profile")

            if st.button("📊 Dashboard"):
                self.emit_event(AppMode.DASHBOARD)
            if self.profile:
                if st.button("✏️ Edit Account"):
                    self.emit_event(AppMode.SETUP_PROFILE)
            else:
                if st.button("➕ Setup Account"):
                    self.emit_event(AppMode.SETUP_PROFILE)

            st.divider()

            st.title("💳 Debt Wizard")
            st.caption("Manage your debt")

            if st.button("💫 Simulate"):
                self.emit_event(AppMode.DEBT_WIZARD)

            st.divider()

            with st.expander("Other Options"):
                upload_profile = st.file_uploader(
                    "Replace profile", accept_multiple_files=False, type="json"
                )
                if upload_profile is not None:
                    json_profile = json.load(upload_profile)
                    with open(".user_profile.json", "w", encoding="utf-8") as f:
                        json.dump(json_profile, f)
                        st.rerun()

                self.state.debug_mode = st.toggle(
                    "Enable Debug Mode", value=self.state.debug_mode
                )

                if self.state.debug_mode:
                    st.json(self.state.model_dump())

    def render_dashboard(self) -> None:
        st.title("📊 Dashboard")

        if self.profile:
            account_name_type = (
                f"Profile: **{self.profile.name}**"
                if not isinstance(self.profile, DebtRepaymentProfile)
                else f"Debt Repayment Profile: **{self.profile.name}**"
            )
            st.caption(account_name_type)

        if self.accounts:
            self.render_account_dashboard()
        else:
            with st.container(border=True):
                st.header("Bank")
                st.info("No bank accounts, go to Setup Profile to add")

        if self.incomes:
            self.render_income_dashboard()
        else:
            with st.container(border=True):
                st.header("Income")
                st.info("No income streams, go to Setup Profile to add")

        if self.debts:
            self.render_debt_dashboard()
        else:
            with st.container(border=True):
                st.header("Debt")
                st.info("No debt, go to Setup Profile to add")
        if self.bills:
            self.render_bills_dashboard()
        else:
            with st.container(border=True):
                st.header("Bills")
                st.info("No bills, go to Setup Profile to add")

    def render_account_dashboard(self) -> None:
        if self.profile:
            with st.container(border=True):
                st.header("Bank")
                table_data = [
                    {
                        "Provider": account.name,
                        "Amount": f"${account.amount:,.2f}",
                    }
                    for account in self.profile.bank_accounts
                ]
                df = pd.DataFrame(table_data)
                st.table(df)

                account_amount_str = f"**${self.profile.total_accounts():,.2f}**"
                account_providers_str = (
                    f"{len(self.profile.bank_accounts)} bank accounts"
                    if len(self.profile.bank_accounts) > 1
                    else "one bank account"
                )
                account_providers_str = str_to_num(account_providers_str)

                st.info(f"You have {account_amount_str} in {account_providers_str}")

    def render_income_dashboard(self) -> None:
        if self.profile:
            with st.container(border=True):
                st.header("Income")
                table_data = [
                    {
                        "Source": income.income_name,
                        "Monthly pay": f"${round(float(income.monthly_amount), 2):,.2f}",
                    }
                    for income in self.profile.income
                ]
                df = pd.DataFrame(table_data)
                st.table(df)

                num_income = str_to_num(
                    f"from {len(self.profile.income)} income streams"
                )

                income_str = (
                    f"You earn **${round(self.profile.monthly_income(), 2):,.2f}** {num_income}"
                    if len(self.profile.income) > 1
                    else f"You earn **${round(self.profile.monthly_income(), 2):,.2f}** from one income stream"
                )

                st.success(income_str)

    def render_debt_dashboard(self) -> None:
        if self.profile:
            with st.container(border=True):
                st.header("Debt")
                table_data = [
                    {
                        "Debtor": debt.name,
                        "Amount": f"${debt.amount:0,.2f}",
                        "APR": float(debt.apr),
                        "Minimum": f"${debt.min:0,.2f}",
                    }
                    for debt in self.profile.debts
                ]
                df = pd.DataFrame(table_data)
                st.table(df)

                debt_amount_str = ""
                debt_amount = float(self.profile.total_debt())
                if debt_amount > 10000:
                    debt_amount_str = f":red[**${debt_amount:,.2f}**]"
                elif 1000 < debt_amount < 10000:
                    debt_amount_str = f":orange[**${debt_amount:,.2f}**]"
                else:
                    debt_amount_str = f":green[**${debt_amount:,.2f}**]"

                debtors_str = ""
                if len(self.profile.debts) > 1:
                    min_payments = [str(d.min) for d in self.debts]
                    num_debtors = str_to_num(f"{len(self.profile.debts)} debtors")
                    debtors_str = f"{num_debtors} and must pay **\\${', \\$'.join(min_payments)}** monthly"
                else:
                    debtors_str = "one debtor"

                st.error(f"You have {debt_amount_str} of debt from {debtors_str}")

    def render_bills_dashboard(self) -> None:
        if self.profile:
            with st.container(border=True):
                st.header("Bills")
                table_data = [
                    {
                        "Name": bill.name,
                        "Type": bill.bill_type,
                        "Amount": f"${bill.amount:,.2f}",
                    }
                    for bill in self.profile.bills
                ]
                df = pd.DataFrame(table_data)
                st.table(df)

                amount_str = f"**\\${round(self.profile.monthly_bills(), 2):,.2f}**"
                billers_str = (
                    f"{len(self.profile.bills)} bills"
                    if len(self.profile.bills) > 1
                    else "one bill"
                )
                billers_str = str_to_num(billers_str)

                st.warning(
                    f"You pay {amount_str} from {billers_str}, leaving you with **\\${self.profile.monthly_income() - self.profile.monthly_bills():,.2f}** for the month"
                )

    def setup_profile(self) -> None:
        if not self.profile:
            st.title("➕ Setup Account")
        else:
            st.title("✏️ Edit Account")

        info_tab, accounts_tab, incomes_tab, loans_tab, bills_tab = st.tabs(
            ["Info", "Bank Accounts", "Income", "Loans", "Bills"]
        )

        with info_tab:
            new_user_name = (
                st.text_input("Name")
                if not self.profile
                else st.text_input("Name", value=self.profile.name)
            )

            if self.profile:
                self.profile.name = new_user_name
            elif (
                st.session_state.accounts
                and st.session_state.incomes
                and st.session_state.debts
                and st.session_state.bills
            ):
                profile = Profile(
                    name=new_user_name,
                    bank_accounts=st.session_state.accounts,
                    debts=st.session_state.debts,
                    income=st.session_state.incomes,
                    bills=st.session_state.bills,
                )
                total_income = sum([i.amount for i in profile.income])
                total_debt = sum([d.amount for d in profile.debts])

                table_data = [
                    {
                        "Name": profile.name,
                        "Bank accounts": len(profile.bank_accounts),
                        "Monthly income": f"${total_income} from {str(len(profile.income))} sources",
                        "Total debt": f"${total_debt} from {str(len(profile.debts))} loans",
                    }
                ]
                df = pd.DataFrame(table_data)
                st.table(df)
                if st.button("Create user"):
                    self.profile = profile
                    with open(".user_profile.json", "w", encoding="utf-8") as f:
                        f.write(profile.model_dump_json(indent=4))
            else:
                st.info("Profile not yet created")

            upload_profile = st.file_uploader(
                "Upload profile", accept_multiple_files=False, type="json"
            )
            if upload_profile is not None:
                json_profile = json.load(upload_profile)
                with open(".user_profile.json", "w", encoding="utf-8") as f:
                    json.dump(json_profile, f)
                    st.rerun()

        with accounts_tab:
            st.header("Bank Accounts")

            if st.button("Add bank account"):
                self.add_bank_account()

            if self.accounts:
                with st.expander("Added accounts", expanded=True):
                    head_col1, head_col2, head_col3, head_col4 = st.columns(
                        [3, 2, 2, 1]
                    )
                    head_col1.write("**Bank name**")
                    head_col2.write("**Type**")
                    head_col3.write("**Amount**")
                    head_col4.write("**Remove**")
                    st.divider()

                    for idx, acc in enumerate(self.accounts):
                        col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                        col1.text(acc.name)
                        col2.text(acc.account_type)
                        col3.text(f"${acc.amount:,.2f}")

                        if col4.button("X", key=f"del_acc_{idx}", type="primary"):
                            self.accounts.pop(idx)
                            if self.profile:
                                self.profile.bank_accounts = self.accounts

                            self.save_current()
                            st.rerun()
            else:
                st.info("No accounts added")

        with incomes_tab:
            st.header("Income")

            if st.button("Add income"):
                self.add_income()

            if self.incomes:
                with st.expander("Added accounts", expanded=True):
                    head_col1, head_col2, head_col3 = st.columns([3, 2, 1])
                    head_col1.write("**Source of income**")
                    head_col2.write("**Monthly pay ($)**")
                    head_col3.write("**Remove**")
                    st.divider()

                    for idx, income in enumerate(self.incomes):
                        col1, col2, col3 = st.columns([3, 2, 1])

                        col1.text(income.income_name)
                        col2.text(f"${income.monthly_amount:,.2f}")

                        if col3.button("X", key=f"del_income_{idx}", type="primary"):
                            self.incomes.pop(idx)
                            if self.profile:
                                self.profile.income = self.incomes

                            self.save_current()
                            st.rerun()
            else:
                st.info("No income streams added")

        with loans_tab:
            st.header("Loans")

            if st.button("Add loan"):
                self.add_loan()

            if self.debts:
                with st.expander("Added loans", expanded=True):
                    head_col1, head_col2, head_col3, head_col4, head_col5 = st.columns(
                        [5, 4, 3, 2, 2]
                    )
                    head_col1.write("**Debtor**")
                    head_col2.write("**Amount**")
                    head_col3.write("**APR**")
                    head_col4.write("**Minimum Payment**")
                    head_col5.write("**Remove**")
                    st.divider()

                    for idx, loan in enumerate(self.debts):
                        col1, col2, col3, col4, col5 = st.columns([5, 4, 3, 2, 2])

                        col1.text(loan.name)
                        col2.text(f"${loan.amount:,.2f}")
                        col3.text(loan.apr)
                        col4.text(f"${loan.min:,.2f}")

                        if col5.button("X", key=f"del_debt_{idx}", type="primary"):
                            self.debts.pop(idx)
                            if self.profile:
                                self.profile.debts = self.debts

                            self.save_current()
                            st.rerun()
            else:
                st.info("No loans added")

        with bills_tab:
            st.header("Bills")

            if st.button("Add bill"):
                self.add_bill()

            if self.bills:
                with st.expander("Added bills", expanded=True):
                    head_col1, head_col2, head_col3, head_col4, head_col5 = st.columns(
                        [5, 4, 3, 2, 2]
                    )
                    head_col1.write("**Billing Entity**")
                    head_col2.write("**Type**")
                    head_col3.write("**Amount**")
                    head_col4.write("Range")
                    head_col5.write("Remove")

                    for idx, bill in enumerate(self.bills):
                        col1, col2, col3, col4, col5 = st.columns([5, 4, 3, 2, 2])

                        col1.text(bill.name)
                        col2.text(bill.bill_type)
                        col3.write(f"{bill.amount:,.2f}")
                        col4.write("✅") if bill.randomize else col4.write("❌")

                        if col5.button("X", key=f"del_bill_{idx}", type="primary"):
                            self.bills.pop(idx)
                            if self.profile:
                                self.profile.bills = self.bills

                            self.save_current()
                            st.rerun()
            else:
                st.info("No bills added")

    @st.dialog("Add bank account")
    def add_bank_account(self) -> None:
        with st.form("add_account"):
            st.write("Add Account")
            account_name = st.text_input("Account name")
            account_type: Literal["Checking", "Saving"] = "Checking"

            account_type_selector = st.radio(
                "Account type", options=["Checking", "Saving"]
            )

            if account_type_selector == "Checking":
                account_type = "Checking"
            else:
                account_type = "Saving"

            account_amount = Decimal(
                str(
                    st.number_input(
                        "Amount in account ($)",
                        0.0,
                        100000.0,
                        step=0.01,
                        format="%0.2f",
                    )
                )
            )

            add_account = st.form_submit_button("Add")

            if add_account:
                acc = BankAccount(
                    name=account_name, account_type=account_type, amount=account_amount
                )

                st.session_state.accounts.append(acc)
                if self.profile:
                    self.profile.bank_accounts.append(acc)

                self.save_current()
                st.rerun()

    @st.dialog("Add income")
    def add_income(self) -> None:
        with st.form("add_income"):
            st.write("Add Income")
            name = st.text_input("Source of income")
            amount = Decimal(st.number_input("Bi-weekly amount ($)", 0))

            add_income = st.form_submit_button("Add")

            if add_income:
                income = Income(income_name=name, amount=amount)

                st.session_state.incomes.append(income)
                if self.profile:
                    self.profile.income.append(income)

                self.save_current()
                st.rerun()

    @st.dialog("Add loan")
    def add_loan(self) -> None:
        with st.form("add_loan"):
            st.write("Add Loan")
            name = st.text_input("Provider")
            amount = Decimal(st.number_input("Balance of loan ($)", 0))
            apr = Decimal(
                str(st.number_input("APR", 0.000, 1.000, step=0.001, format="%0.3f"))
            )
            min_pay = Decimal(st.number_input("Minimum payment", 0))

            add_loan = st.form_submit_button("Add")

            if add_loan:
                debt = Debt(name=name, amount=amount, apr=apr, min=min_pay)

                st.session_state.debts.append(debt)
                if self.profile:
                    self.profile.debts.append(debt)

                self.save_current()
                st.rerun()

    @st.dialog("Add bill")
    def add_bill(self) -> None:
        randomize = st.checkbox("Randomize with range", value=False)

        with st.form("add_bill_form"):
            st.write("Add bill details")
            name = st.text_input("Billing entity")

            options: list[BillType] = [
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
            selected_type = st.selectbox("Bill type", options=options)
            bill_type = cast(BillType, selected_type)

            bill_amount = Decimal("0.00")
            bill_range = None

            if randomize:
                col1, col2 = st.columns(2)
                with col1:
                    low = st.number_input(
                        "Low Range ($)", 0.0, step=0.01, format="%0.2f"
                    )
                with col2:
                    high = st.number_input(
                        "High Range ($)", 0.0, step=0.01, format="%0.2f"
                    )
                bill_range = (Decimal(str(low)), Decimal(str(high)))
            else:
                amount_input = st.number_input(
                    "Bill Amount ($)", 0.0, step=0.01, format="%0.2f"
                )
                bill_amount = Decimal(str(amount_input))

            if st.form_submit_button("Add"):
                if not name:
                    st.error("Please enter a name.")
                    return

                new_bill = Bill(
                    name=name,
                    bill_type=bill_type,
                    randomize=randomize,
                    amount=bill_amount,
                    amount_range=bill_range,
                )

                st.session_state.bills.append(new_bill)
                if self.profile:
                    self.profile.bills.append(new_bill)

                self.save_current()
                st.rerun()

    def save_current(self) -> None:
        if Path(".user_profile.json").exists() and self.profile:
            with open(".user_profile.json", "w", encoding="utf-8") as f:
                f.write(self.profile.model_dump_json(indent=4))

    def simulate(self) -> None:
        st.title("💫 Simulate")
        if self.profile and not isinstance(self.profile, DebtRepaymentProfile):
            st.info("You don't have a debt repayment profile type")
            if st.button("Would you like to convert your profile?", type="primary"):
                self.profile.debt_repayment = True
                with open(".user_profile.json", "w", encoding="utf-8") as f:
                    f.write(self.profile.model_dump_json(indent=4))
                self.load_account()
                st.rerun()
        elif self.profile and isinstance(self.profile, DebtRepaymentProfile):
            with st.container(border=True):
                st.header("Monthly payments")

                with st.container():
                    st.subheader("Loan Options")
                    adjust_rent = st.number_input(
                        label="Current Rent",
                        format="%0.2f",
                        value=round(float(self.profile.rent), 2),
                    )

                    if Decimal(str(adjust_rent)) != self.profile.rent:
                        st.write("Yeh")
                        self.profile.rent = Decimal(str(adjust_rent))
                        for bill in self.profile.bills:
                            if bill.bill_type == "Rent" and bill.amount:
                                bill.amount = self.profile.rent
                        for bill in st.session_state.bills:
                            if bill.bill_type == "Rent" and bill.amount:
                                bill.amount = self.profile.rent

                    col1, col2 = st.columns(2)

                    set_high_apr = col1.number_input(
                        "Minimum payment for highest APR loan",
                        min_value=0.0,
                        value=float(self.profile.highest_apr_amount),
                    )
                    set_last_loan = col2.number_input(
                        "Minimum payment for last remaining loan",
                        min_value=0.0,
                        value=float(self.profile.last_debt_amount),
                    )

                    if st.button("Update Options", type="primary"):
                        self.profile.highest_apr_amount = Decimal(str(set_high_apr))
                        self.profile.last_debt_amount = Decimal(str(set_last_loan))
                        self.save_current()

                if isinstance(self.profile, DebtRepaymentProfile):
                    st.subheader("Monthly payments")
                    instructions_str, total_months = (
                        self.profile.simulate_loan_evisceration()
                    )

                    years, months = divmod(total_months, 12)
                    info_str = (
                        f"With current options, it would take {years} years, {months} months to completely pay off your loans"
                        if years > 0
                        else f"With current options, it would take {months} months to completely pay off your loans"
                    )

                    if years >= 10:
                        st.error(info_str)
                    elif 4 <= years < 10:
                        st.warning(info_str)
                    elif 1 <= years < 4:
                        st.info(info_str)
                    elif years < 1:
                        st.success(info_str)

                    with st.expander("Details"):
                        st.markdown(instructions_str)

    def load_account(self):
        if Path(".user_profile.json").exists():
            with open(".user_profile.json", "r", encoding="utf-8") as f:
                profile_json = json.load(f)
                profile = Profile.model_validate(profile_json)
                if profile.debt_repayment:
                    profile = DebtRepaymentProfile.model_validate(profile_json)
                self.profile = profile
                self.accounts = self.profile.bank_accounts
                self.debts = self.profile.debts
                self.incomes = self.profile.income
                self.bills = self.profile.bills

    def run(self) -> None:
        self.render_sidebar()

        view_function = self.routes.get(self.state.active_mode, self.render_dashboard)
        view_function()
