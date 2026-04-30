import json
import pandas as pd
import streamlit as st

from decimal import Decimal
from enum import auto, Enum
from pathlib import Path
from pydantic import BaseModel, ConfigDict, Field

from src.helpers.get_profile import GetProfile
from src.helpers.str_to_num import str_to_num

from src.models import (
    BankAccount,
    Bill,
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
    PLAYGROUND = auto()


class AppState(BaseModel):
    """Used for handling simple options for the app."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    active_mode: AppMode = AppMode.DASHBOARD
    user_name: str = "Guest"
    debug_mode: bool = False
    run_count: int = Field(default=0, ge=0)


class PersonalFinances:
    """The `streamlit`-powered GUI for the application."""

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
            AppMode.PLAYGROUND: self.playground,
        }

        self.get_profile = GetProfile()

        self.state.user_name = self.get_profile.name
        self.data = self.get_profile.data
        self.load_account()

        if self.state.user_name == "Guest" and st.session_state.run_count == 0:
            self.state.active_mode = AppMode.SETUP_PROFILE

        self.load_account()

    def start_app(self) -> None:
        """A custom app runner for the application."""
        with st.sidebar:
            st.logo("🪙")
        dashboard_pg = st.Page(
            self.render_dashboard,
            title="Dashboard",
            icon="📊",
            default=(self.state.active_mode == AppMode.DASHBOARD),
        )

        profile_label = "Edit Profile" if self.profile else "Setup Profile"
        profile_icon = "✏️" if self.profile else "➕"
        profile_pg = st.Page(self.setup_profile,
                             title=profile_label, icon=profile_icon)
        options_pg = st.Page(self.preferences, title="Preferences", icon="⚙️")
        playground_pg = st.Page(self.playground, title="Playground", icon="🛝")

        wizard_pg = st.Page(self.simulate, title="Simulate", icon="💫")

        pages = {
            f"Welcome, {self.state.user_name}": [dashboard_pg, profile_pg, options_pg],
            "Debt Wizard": [wizard_pg],
            "Developer Tools": [playground_pg],
        }

        pg = st.navigation(pages, expanded=2)

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

                st.info(
                    f"You have {account_amount_str} in {account_providers_str}")

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
                    num_debtors = str_to_num(
                        f"{len(self.profile.debts)} debtors")
                    debtors_str = f"{num_debtors} and must pay **\\${', \\$'.join(min_payments)}** monthly"
                else:
                    debtors_str = "one debtor"

                st.error(
                    f"You have {debt_amount_str} of debt from {debtors_str}")

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
        if "show_toast" in st.session_state:
            st.toast(st.session_state["show_toast"])
            del st.session_state["show_toast"]

        if not self.profile:
            st.title("➕ Setup Profile")
        else:
            st.title("✏️ Edit Profile")

        info_tab, accounts_tab, incomes_tab, loans_tab, bills_tab = st.tabs(
            ["Info", "Bank Accounts", "Income", "Loans", "Bills"]
        )

        with info_tab:
            st.header("Info")

            new_user_name = (
                st.text_input("Name")
                if not self.profile
                else st.text_input("Name", value=self.profile.name)
            )

            if self.profile:
                if st.button("Update Name", type="primary"):
                    self.profile.name = new_user_name
                    self.save_current()
                    st.rerun()
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

            if self.profile:
                st.header("Export")

                profile_json_string = self.profile.model_dump_json(
                    exclude={"logs"}, indent=4
                )
                st.download_button(
                    label="Export Profile",
                    data=profile_json_string,
                    file_name="user_profile.json",
                    mime="application/json",
                )

        with accounts_tab:
            st.header("Bank Accounts")
            if self.accounts:
                account_types = ["Checking", "Saving"]
                accounts_table = [
                    {
                        "Bank name": acc.name,
                        "Type": acc.account_type,
                        "Amount": str(acc.amount),
                        "Remove": False,
                    }
                    for acc in self.accounts
                ]
                df_accounts = pd.DataFrame(accounts_table)
                acc_key = f"accounts_editor_{self.state.run_count}"
                edited_df = st.data_editor(
                    df_accounts,
                    key=acc_key,
                    hide_index=True,
                    column_config={
                        "Bank name": st.column_config.TextColumn(default="Bank"),
                        "Type": st.column_config.SelectboxColumn(
                            "Account Category",
                            options=account_types,
                            required=True,
                        ),
                        "Amount": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "Remove": st.column_config.CheckboxColumn(),
                    },
                    width="stretch",
                    num_rows="add",
                )

                if st.button("Update Accounts", type="primary"):
                    final_df = edited_df[~edited_df["Remove"]].copy()
                    new_accounts_list = []
                    for _, row in final_df.iterrows():
                        name = (
                            str(row["Bank name"]).strip()
                            if not pd.isna(row["Bank name"])
                            else "Bank"
                        )
                        amt = pd.to_numeric(
                            row["Amount"], errors="coerce") or 0.0
                        new_accounts_list.append(
                            BankAccount(
                                name=name,
                                account_type=row["Type"],
                                amount=Decimal(str(round(amt, 2))),
                            )
                        )
                    self.accounts = new_accounts_list
                    if self.profile:
                        self.profile.bank_accounts = self.accounts
                    self.save_current()
                    st.session_state["show_toast"] = "Updated accounts"
                    st.rerun()
            else:
                st.info("No accounts added")

        with incomes_tab:
            st.header("Income")
            if self.incomes:
                incomes_table = [
                    {
                        "Source of income": inc.income_name,
                        "Biweekly pay": str(inc.amount),
                        "Remove": False,
                    }
                    for inc in self.incomes
                ]
                df_incomes = pd.DataFrame(incomes_table)
                inc_key = f"incomes_editor_{self.state.run_count}"
                edited_df = st.data_editor(
                    df_incomes,
                    key=inc_key,
                    hide_index=True,
                    column_config={
                        "Source of income": st.column_config.TextColumn(default="Job"),
                        "Biweekly pay": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "Remove": st.column_config.CheckboxColumn(),
                    },
                    width="stretch",
                    num_rows="add",
                )

                if st.button("Update Income", type="primary"):
                    final_df = edited_df[~edited_df["Remove"]].copy()
                    new_incomes_list = []
                    for _, row in final_df.iterrows():
                        name = (
                            str(row["Source of income"]).strip()
                            if not pd.isna(row["Source of income"])
                            else "Job"
                        )
                        amt = pd.to_numeric(
                            row["Biweekly pay"], errors="coerce") or 0.0
                        new_incomes_list.append(
                            Income(
                                income_name=name,
                                amount=Decimal(str(round(amt, 2))),
                            )
                        )
                    self.incomes = new_incomes_list
                    if self.profile:
                        self.profile.income = self.incomes
                    self.save_current()
                    st.session_state["show_toast"] = "Updated income"
                    st.rerun()
            else:
                st.info("No income streams added")

        with loans_tab:
            st.header("Loans")
            if self.debts:
                debt_table = [
                    {
                        "Debtor": d.name,
                        "Amount": str(d.amount),
                        "APR": str(d.apr),
                        "Min payment": d.min,
                        "Remove": False,
                    }
                    for d in self.debts
                ]
                df_debts = pd.DataFrame(debt_table)
                debt_key = f"debts_editor_{self.state.run_count}"
                edited_df = st.data_editor(
                    df_debts,
                    key=debt_key,
                    hide_index=True,
                    column_config={
                        "Debtor": st.column_config.TextColumn(default="Debtor"),
                        "Amount": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "APR": st.column_config.NumberColumn(
                            format="%.4f", default=0.05
                        ),
                        "Min payment": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "Remove": st.column_config.CheckboxColumn(),
                    },
                    width="stretch",
                    num_rows="add",
                )

                if st.button("Update Debt", type="primary"):
                    final_df = edited_df[~edited_df["Remove"]].copy()
                    new_debts_list = []
                    for _, row in final_df.iterrows():
                        name = (
                            str(row["Debtor"]).strip()
                            if not pd.isna(row["Debtor"])
                            else "Debtor"
                        )
                        amt = pd.to_numeric(
                            row["Amount"], errors="coerce") or 0.0
                        apr = pd.to_numeric(
                            row["APR"], errors="coerce") or 0.05
                        mp = pd.to_numeric(
                            row["Min payment"], errors="coerce") or 0.0
                        new_debts_list.append(
                            Debt(
                                name=name,
                                amount=Decimal(str(round(amt, 2))),
                                apr=Decimal(str(round(apr, 4))),
                                min=Decimal(str(round(mp, 2))),
                            )
                        )
                    self.debts = new_debts_list
                    if self.profile:
                        self.profile.debts = self.debts
                    self.save_current()
                    st.session_state["show_toast"] = "Updated debts"
                    st.rerun()
            else:
                st.info("No loans added")

        with bills_tab:
            st.header("Bills")
            if self.bills:
                bill_types = [
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
                bills_table = [
                    {
                        "Billing entity": b.name,
                        "Type": b.bill_type,
                        "Amount": float(b.amount) if b.amount else 0.0,
                        "Min amount": float(b.amount_range[0])
                        if b.amount_range
                        else 0.0,
                        "Max amount": float(b.amount_range[1])
                        if b.amount_range
                        else 0.0,
                        "Remove": False,
                    }
                    for b in self.bills
                ]
                df_bills = pd.DataFrame(bills_table)
                bill_key = f"bills_editor_{self.state.run_count}"
                edited_df = st.data_editor(
                    df_bills,
                    key=bill_key,
                    hide_index=True,
                    column_config={
                        "Billing entity": st.column_config.TextColumn(
                            default="New Bill"
                        ),
                        "Type": st.column_config.SelectboxColumn(
                            "Bill Category", options=bill_types, required=True
                        ),
                        "Amount": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "Min amount": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "Max amount": st.column_config.NumberColumn(
                            format="$%,.2f", default=0.0
                        ),
                        "Remove": st.column_config.CheckboxColumn(),
                    },
                    width="stretch",
                    num_rows="add",
                )

                if st.button("Update Bills", type="primary"):
                    final_df = edited_df[~edited_df["Remove"]].copy()
                    new_bills_list = []
                    for _, row in final_df.iterrows():
                        name = (
                            str(row["Billing entity"]).strip()
                            if not pd.isna(row["Billing entity"])
                            else "New Bill"
                        )
                        amt = pd.to_numeric(
                            row["Amount"], errors="coerce") or 0.0
                        mi = pd.to_numeric(
                            row["Min amount"], errors="coerce") or 0.0
                        ma = pd.to_numeric(
                            row["Max amount"], errors="coerce") or 0.0
                        has_range = mi > 0 and ma > 0
                        new_bills_list.append(
                            Bill(
                                name=name,
                                bill_type=row["Type"],
                                amount=Decimal(str(round(amt, 2)))
                                if not has_range
                                else Decimal("0"),
                                amount_range=(
                                    (
                                        Decimal(str(round(mi, 2))),
                                        Decimal(str(round(ma, 2))),
                                    )
                                )
                                if has_range
                                else None,
                                randomize=has_range,
                            )
                        )
                    self.bills = new_bills_list
                    if self.profile:
                        self.profile.bills = self.bills
                    self.save_current()
                    st.session_state["show_toast"] = "Updated bills"
                    st.rerun()
            else:
                st.info("No bills added")

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
                        self.profile.highest_apr_amount = Decimal(
                            str(set_high_apr))
                        self.profile.last_debt_amount = Decimal(
                            str(set_last_loan))
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

    def playground(self):
        st.title("🛝 Playground")

        play_area_one, play_area_two, play_area_three = st.tabs(
            ["Play Area 1", "Play Area 2", "Play Area 3"]
        )

        with play_area_one:
            st.header("Play Area 1")

            profile_type = "Profile"
            if isinstance(self.profile, DebtRepaymentProfile):
                profile_type = "Debt Repayment Profile"

            with st.popover(profile_type):
                st.help(self.profile)

        with play_area_two:
            st.header("Play Area 2")

            if "messages" not in st.session_state:
                st.session_state.messages = [
                    {"role": "assistant", "content": "Enter the name of this bill"}]
            if "bill_step" not in st.session_state:
                st.session_state.bill_step = "name"
            if "bill_data" not in st.session_state:
                st.session_state.bill_data = {}

            bill_types = ["Internet", "Utilities", "Groceries", "Phones", "Games",
                          "Music", "Entertainment", "Daycare", "Rent", "Extra spending"]
            
            chat_container = st.container(height=400)
            for message in st.session_state.messages:
                chat_container.chat_message(message["role"]).write(message["content"])
            
            if prompt := st.chat_input("Reply"):
                chat_container.chat_message("user").write(prompt)
                st.session_state.messages.append({"role": "user", "content": prompt})

                if st.session_state.bill_step == "name":
                    st.session_state.bill_data["name"] = prompt
                    response = f"What kind of bill is {prompt}? \n\nOptions: {', '.join(bill_types)}"
                    st.session_state.bill_step = "type"
                
                elif st.session_state.bill_step == "type":
                    st.session_state.bill_data["type"] = prompt
                    response = f"What is the amount for the {prompt} bill '{st.session_state.bill_data['name']}'?"
                    st.session_state.bill_step = "amount"
                
                elif st.session_state.bill_step == "amount":
                    try:
                        amount = Decimal(prompt.replace("$", ""))
                        st.session_state.bill_data["amount"] = amount
                        response = f"✅ Bill Created! \n\n **Name:** {st.session_state.bill_data['name']} \n\n **Type:** {st.session_state.bill_data['type']} \n\n **Amount:** ${amount}"
                        st.session_state.bill_step = "complete"
                    except:
                        response = "Please enter a valid numerical amount (e.g., 50.00)."
                
                st.session_state.messages.append({"role": "assistant", "content": response})
                st.rerun()

        with play_area_three:
            st.header("Play Area 3")

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
        view_function = self.routes.get(
            self.state.active_mode, self.render_dashboard)
        view_function()
