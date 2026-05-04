import json
import pandas as pd
import streamlit as st

from datetime import datetime
from pathlib import Path
from typing import Literal

import src.models as models

ACCOUNT_TYPES: list[Literal["Checking", "Saving"]] = ["Checking", "Saving"]
BILL_TYPES: list[
    Literal[
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
] = [
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

if ".profile.json" not in st.session_state:
    st.session_state[".profile.json"] = {}

if Path(".profile.json").exists():
    with open(".profile.json", "r", encoding="utf-8") as file:
        st.session_state[".profile.json"] = json.load(file)

if "profile_name" not in st.session_state:
    st.session_state.profile_name = "Guest"

if "accounts_df" not in st.session_state:
    accounts_data: dict[str, list[str | bool]] = {
        "Bank name": ["Bank"],
        "Type": [ACCOUNT_TYPES[0]],
        "Amount": ["0.00"],
        "Remove": [False],
    }
    st.session_state.accounts_df = pd.DataFrame(accounts_data)

if "income_df" not in st.session_state:
    income_data: dict[str, list[str | bool]] = {
        "Source of income": ["Job"],
        "Bi-weekly pay": ["0.00"],
        "Remove": [False],
    }
    st.session_state.income_df = pd.DataFrame(income_data)

if "bills_df" not in st.session_state:
    bills_data: dict[str, list[str | bool]] = {
        "Billing entity": ["Biller"],
        "Type": [BILL_TYPES[0]],
        "Amount": ["0.00"],
        "Min amount": ["0.00"],
        "Max amount": ["0.00"],
        "Remove": [False],
    }
    st.session_state.bills_df = pd.DataFrame(bills_data)

if "debt_df" not in st.session_state:
    debt_data: dict[str, list[str | bool]] = {
        "Debtor": ["Debtor"],
        "Amount": ["0.00"],
        "APR": ["0.050"],
        "Min payment": ["0.00"],
        "Remove": [False],
    }
    st.session_state.debt_df = pd.DataFrame(debt_data)


def show_data_editor(data_type: str):
    _map: dict[str, pd.DataFrame] = {
        "bank accounts": st.session_state.accounts_df,
        "income": st.session_state.income_df,
        "bills": st.session_state.bills_df,
        "debt": st.session_state.debt_df,
    }

    _session_state = _map[data_type]
    _config = {
        "bank accounts": {
            "Bank name": st.column_config.TextColumn(default="Bank"),
            "Type": st.column_config.SelectboxColumn(
                "Account Category", options=ACCOUNT_TYPES, required=True
            ),
            "Amount": st.column_config.NumberColumn(
                format="$%,.2f", default=0.00, min_value=0
            ),
            "Remove": st.column_config.CheckboxColumn(default=False),
        },
        "income": {
            "Source of income": st.column_config.TextColumn(default="Job"),
            "Bi-weekly pay": st.column_config.NumberColumn(
                format="$%,.2f", default=0.00, min_value=0
            ),
            "Remove": st.column_config.CheckboxColumn(default=False),
        },
        "bills": {
            "Billing entity": st.column_config.TextColumn(default="New Bill"),
            "Type": st.column_config.SelectboxColumn(
                "Bill Category", options=BILL_TYPES, required=True
            ),
            "Amount": st.column_config.NumberColumn(
                format="$%,.2f", default=0.00, min_value=0
            ),
            "Min amount": st.column_config.NumberColumn(
                format="$%,.2f", default=0.00, min_value=0
            ),
            "Max amount": st.column_config.NumberColumn(
                format="$%,.2f", default=0.00, min_value=0
            ),
            "Remove": st.column_config.CheckboxColumn(default=False),
        },
        "debt": {
            "Debtor": st.column_config.TextColumn(default="Debtor"),
            "Amount": st.column_config.NumberColumn(format="$%,.2f", default=0.00),
            "APR": st.column_config.NumberColumn(format="%.4f", default=0.050),
            "Min payment": st.column_config.NumberColumn(
                format="$%,.2f", default=0.0, min_value=0
            ),
            "Remove": st.column_config.CheckboxColumn(default=False),
        },
    }

    st.subheader(f"Add {data_type.lower()}")

    edited_df = st.data_editor(
        _session_state,
        key=f"{data_type}_editor",
        hide_index=True,
        column_config=_config[data_type],
        width="stretch",
        num_rows="add",
    )

    button_label = "Update & Remove" if edited_df["Remove"].any() else "Update"

    _, button_col = st.columns([3, 1])

    with button_col:
        if st.button(button_label, key=f"{data_type}_button", type="primary", width="stretch"):
            _session_state = edited_df[~edited_df["Remove"]].reset_index(drop=True)
            st.rerun()


st.title("Profile")
st.caption(f"**{st.session_state.profile_name}'s** profile")

with st.expander("Setup Profile"):
    name_input_col, name_button_col = st.columns([3, 1], vertical_alignment="bottom")

    with name_input_col:
        name_input = st.text_input("Your name", value=st.session_state.profile_name, key="name_input_key")

    with name_button_col:
        has_changed = st.session_state.name_input_key != st.session_state.profile_name

        if st.button(
            "Update",
            key="updated_name_button",
            width="stretch",
            type="primary",
            disabled=not has_changed
        ):
            st.session_state.profile_name = st.session_state.name_input_key
            st.rerun()
        
    for data_type in ["bank accounts", "income", "bills", "debt"]:
        show_data_editor(data_type)
    
_, button_col = st.columns([3, 1])

prev_data = False

with button_col:
    if st.button("Update Profile", key="update_profile_button", type="primary", width="stretch"):
        _name = st.session_state.profile_name
        _today = datetime.today()
        _current_date = _today
        _bank_accounts = st.session_state.accounts_df
        _income = st.session_state.income_df
        _bills = st.session_state.bills_df
        _debt = st.session_state.debt_df

        prev_data = _bank_accounts

        # create the best corresponding json file

if not isinstance(prev_data, bool):
    for k, v in prev_data.items():
        st.write(k)
        st.write(v)