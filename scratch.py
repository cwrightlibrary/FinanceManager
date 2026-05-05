if st.button("Export Profile JSON", type="primary"):
    # 1. Helper to format numbers to strings (e.g., 0.0 -> "0.00")
    def to_str(val, decimals=2):
        return f"{float(val):.{decimals}f}"

    # 2. Process Bank Accounts
    bank_list = []
    for _, row in st.session_state.bank_accounts_df.iterrows():
        bank_list.append({
            "name": row["Bank name"],
            "account_type": row["Type"],
            "amount": to_str(row["Amount"])
        })

    # 3. Process Income
    income_list = []
    for _, row in st.session_state.income_df.iterrows():
        income_list.append({
            "income_name": row["Source of income"],
            "amount": to_str(row["Bi-weekly pay"]),
            "monthly_amount": to_str(float(row["Bi-weekly pay"]) * 2) # Example calc
        })

    # 4. Process Debts
    debt_list = []
    for _, row in st.session_state.debts_df.iterrows():
        debt_list.append({
            "name": row["Debtor"],
            "amount": to_str(row["Amount"]),
            "apr": to_str(row["APR"], 4),
            "min": to_str(row["Min payment"])
        })

    # 5. Process Bills (with the amount_range list)
    bill_list = []
    for _, row in st.session_state.bills_df.iterrows():
        bill_list.append({
            "name": row["Billing entity"],
            "bill_type": row["Type"],
            "randomize": False,
            "amount": to_str(row["Amount"]),
            "amount_range": [to_str(row["Min"], 1), to_str(row["Max"], 1)]
        })

    # 6. Construct Final Payload
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
                ["191950", "0.32"]
            ],
            "capital_gains_rate": "0.15"
        },
        "capital_gains": "0",
        "debt_repayment": True
    }

    with open("profile.json", "w") as f:
        json.dump(payload, f, indent=4)

    st.success("Profile saved to profile.json")