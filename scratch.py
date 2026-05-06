import streamlit as st

def page1():
    st.title("Create your account")

    st.write("Create an account now and take control of your finances.")
    
    account_form = st.form("create_account_form")

    first_name_col, last_name_col = account_form.columns(2)

    first_name_col.text_input("First name", placeholder="John")
    last_name_col.text_input("Last name", placeholder="Smith")
    account_form.text_input("Your email", placeholder="john.smith@email.com")

    if account_form.form_submit_button("Create account", icon=":material/add_circle:", type="primary"):
        st.write("Account created")

def page2():
    st.title("Manage your account")

def page3():
    st.title("Learn about us")

def page4():
    st.title("Try it out")

pages = {
    "Your account": [
        st.Page(page1, title="Create your account"),
        st.Page(page2, title="Manage your account"),
    ],
    "Resources": [
        st.Page(page3, title="Learn about us"),
        st.Page(page4, title="Try it out"),
    ],
}

logo_path = "src/logo_test.png"
st.logo(logo_path, size="large")

pg = st.navigation(pages, position="top")
pg.run()