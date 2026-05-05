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

MAPPING = {
    "bank_accounts": {"name": "Bank name", "account_type": "Type", "amount": "Amount"},
    "income": {"income_name": "Source of income", "amount": "Bi-weekly pay"},
    "debts": {"name": "Debtor", "amount": "Amount", "apr": "APR", "min": "Min payment"},
    "bills": {"name": "Billing entity", "bill_type": "Type", "amount": "Amount"},
}

# --- State initialization ---

# Load existing data
profile_path = Path(".profile.json")
initial_data = json.loads(profile_path.read_text()) if profile_path.exists() else {}

if initial_data and initial_data["name"]:
    st.session_state.profile_name = initial_data["name"]

if "profile_name" not in st.session_state:
    st.session_state.profile_name = "Guest"

for key, schema in CONFIG.items():
    state_key = f"{key}_df"
    if state_key not in st.session_state:
        raw_list = initial_data.get(key, [])

        processed_rows = []
        if raw_list:
            for item in raw_list:
                new_row = {}
                map_dict = MAPPING.get(key, {})

                for json_key, df_col in map_dict.items():
                    new_row[df_col] = item.get(json_key)

                if key == "bills" and "amount_range" in item:
                    new_row["Min"] = item["amount_range"][0]
                    new_row["Max"] = item["amount_range"][1]

                new_row["Remove"] = False
                processed_rows.append(new_row)

        if not processed_rows:
            processed_rows = [schema["defaults"]]

        st.session_state[state_key] = pd.DataFrame(processed_rows)


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


def generate_payload() -> dict:
    def to_str(val, decimals=2) -> str:
        return f"{float(val):.{decimals}f}"

    bank_list = []
    for _, row in st.session_state.bank_accounts_df.iterrows():
        bank_list.append(
            {
                "name": row["Bank name"],
                "account_type": row["Type"],
                "amount": to_str(row["Amount"]),
            }
        )

    income_list = []
    for _, row in st.session_state.income_df.iterrows():
        income_list.append(
            {
                "income_name": row["Source of income"],
                "amount": to_str(row["Bi-weekly pay"]),
            }
        )

    debt_list = []
    for _, row in st.session_state.debts_df.iterrows():
        debt_list.append(
            {
                "name": row["Debtor"],
                "amount": to_str(row["Amount"]),
                "apr": to_str(row["APR"], 4),
                "min": to_str(row["Min payment"]),
            }
        )

    bill_list = []
    for _, row in st.session_state.bills_df.iterrows():
        bill_list.append(
            {
                "name": row["Billing entity"],
                "bill_type": row["Type"],
                "randomize": False
                if to_str(row["Min"]) == "0.00" and to_str(row["Max"]) == "0.00"
                else True,
                "amount": to_str(row["Amount"]),
                "amount_range": [to_str(row["Min"]), to_str(row["Max"])],
            }
        )

    now_ts = datetime.now().isoformat()
    payload = {
        "name": st.session_state.profile_name,
        "start_date": now_ts,
        "current_date": now_ts,
        "bank_accounts": bank_list,
        "debts": debt_list,
        "income": income_list,
        "bills": bill_list,
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
        "debt_repayment": True
        if len(debt_list) > 0 and float(debt_list[0]["amount"]) > 0
        else False,
    }
    return payload


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

if st.button("Save Profile", type="primary"):
    payload = generate_payload()

    if payload["debt_repayment"]:
        st.session_state.profile = models.DebtRepaymentProfile(**payload)
    else:
        st.session_state.profile = models.Profile(**payload)

    with open(".profile.json", "w") as f:
        f.write(st.session_state.profile.model_dump_json(indent=4))

    st.success("Profile saved!")
