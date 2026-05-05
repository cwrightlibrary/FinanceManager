import json
import pandas as pd
import streamlit as st
from pathlib import Path
from datetime import datetime

import src.models as models

# --- Configuration ---
DOLLAR_FORMAT = "$%,.2f"
CONFIG: dict[str, dict] = {
    "bank_accounts": {
        "label": "Bank Accounts",
        "defaults": {
            "Bank name": "Bank",
            "Type": "Checking",
            "Amount": 0.0,
            "Remove": False,
        },
        "options": {"Type": ["Checking", "Saving"]},
        "format": {
            "Amount": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "Remove": st.column_config.CheckboxColumn(
                help="Check to delete this row", default=False
            ),
        },
    },
    "income": {
        "label": "Income",
        "defaults": {"Source of income": "Job", "Bi-weekly pay": 0.0, "Remove": False},
        "format": {
            "Bi-weekly pay": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "Remove": st.column_config.CheckboxColumn(
                help="Check to delete this row", default=False
            ),
        },
    },
    "bills": {
        "label": "Bills",
        "defaults": {
            "Billing entity": "Biller",
            "Type": "Rent",
            "Amount": 0.0,
            "Min": 0.0,
            "Max": 0.0,
            "Remove": False,
        },
        "options": {
            "Type": [
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
        },
        "format": {
            "Amount": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "Min": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "Max": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "Remove": st.column_config.CheckboxColumn(
                help="Check to delete this row", default=False
            ),
        },
    },
    "debts": {
        "label": "Debt",
        "defaults": {
            "Debtor": "Debtor",
            "Amount": 0.0,
            "APR": 0.05,
            "Min payment": 0.0,
            "Remove": False,
        },
        "format": {
            "Amount": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "APR": st.column_config.NumberColumn(
                format="%.4f", min_value=0.0, default=0.05
            ),
            "Min payment": st.column_config.NumberColumn(
                format=DOLLAR_FORMAT, min_value=0.0, default=0.0
            ),
            "Remove": st.column_config.CheckboxColumn(
                help="Check to delete this row", default=False
            ),
        },
    },
}

# --- State initialization ---
if "profile_name" not in st.session_state:
    st.session_state.profile_name = "Guest"

# Load existing data
profile_path = Path(".profile.json")
initial_data = json.loads(profile_path.read_text()) if profile_path.exists() else {}

for key, schema in CONFIG.items():
    state_key = f"{key}_df"
    if state_key not in st.session_state:
        data = initial_data.get(
            key if key != "accounts" else "bank_accounts", [schema["defaults"]]
        )
        st.session_state[state_key] = pd.DataFrame(data)


# --- Helpers ---
def render_editor(key):
    schema = CONFIG[key]
    state_key = f"{key}_df"

    st.subheader(f"Manage {schema['label']}")

    col_cfg = {}

    if "options" in schema:
        for col, opts in schema["options"].items():
            col_cfg[col] = st.column_config.SelectboxColumn(
                options=opts, default=opts[0], required=True
            )

    col_cfg.update(schema.get("format", {}))

    col_cfg["Remove"] = st.column_config.CheckboxColumn(
        "Remove", help="Check to delete this row", default=False
    )

    for col, val in schema["defaults"].items():
        if col not in col_cfg:
            col_cfg[col] = st.column_config.TextColumn(default=val)

    edited_df = st.data_editor(
        st.session_state[state_key],
        key=f"{key}_editor",
        hide_index=True,
        column_config=col_cfg,
        num_rows="add",
        width="stretch",
    )

    if st.button(f"Update {schema['label']}", key=f"btn_{key}"):
        st.session_state[state_key] = edited_df[~edited_df["Remove"]].reset_index(
            drop=True
        )
        st.rerun()


# --- UI layout ---
st.title("Profile")
st.caption(f"**{st.session_state.profile_name}'s** profile")

with st.expander("Setup Profile", expanded=True):
    # Name update section
    new_name = st.text_input("Your name", value=st.session_state.profile_name)
    if st.button("Update Name") and new_name != st.session_state.profile_name:
        st.session_state.profile_name = new_name
        st.rerun()

    for key in CONFIG:
        render_editor(key)

if st.button("Create Profile"):
    payload = {
        "name": st.session_state.profile_name,
        "start_date": str(datetime.now()),
        "current_date": str(datetime.now()),
        **{
            k: st.session_state[f"{k}_df"]
            .drop(columns=["Remove"])
            .to_dict(orient="records")
            for k in CONFIG
        },
        "tax_system": {
            "brackets": [
                ["0", "0.10"],
                ["11600", "0.12"],
                ["47150", "0.22"],
                ["100525", "0.24"],
                ["191950", "0.32"],
            ],
            "capital_gains_rate": "0.15",
        },
        "capital_gains": "0",
        "debt_repayment": False,
    }
    # st.session_state.profile = models.Profile(**payload)
    # st.write(type(st.session_state.profile))

if st.button("Export Profile JSON", type="primary"):
    payload = {
        "name": st.session_state.profile_name,
        "start_date": str(datetime.now()),
        "current_date": str(datetime.now()),
        **{
            k: st.session_state[f"{k}_df"]
            .drop(columns=["Remove"])
            .to_dict(orient="records")
            for k in CONFIG
        },
        "tax_system": {
            "brackets": [
                ["0", "0.10"],
                ["11600", "0.12"],
                ["47150", "0.22"],
                ["100525", "0.24"],
                ["191950", "0.32"],
            ],
            "capital_gains_rate": "0.15",
        },
        "capital_gains": "0",
        "debt_repayment": False,
    }

    with open("profile.json", "w") as f:
        json.dump(payload, f, indent=4)

    st.success("Profile saved to test.json")
