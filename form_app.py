import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os
import base64
from urllib.parse import unquote
import segment_selector  # 🔁 make sure this file has `handle_segment_selection()` defined

# ----------------- SEGMENT CLICK HANDLER ----------------- #
query_params = st.query_params
email_param = query_params.get("email", [None])[0]
segment_param = query_params.get("segment", [None])[0]

if email_param and segment_param:
    email_param = unquote(email_param).strip().lower()
    segment_param = unquote(segment_param).strip()
    segment_selector.handle_segment_selection(email_param, segment_param)

    st.set_page_config(page_title="You're In!", page_icon="✅")
    st.title("✅ You're All Set!")
    st.success(f"You've been added to the **{segment_param}** segment. Keep an eye on your inbox for upcoming emails.")
    st.stop()

# ----------------- CONFIG ----------------- #
CONFIG = {
    "sheet_name": "dcg_contacts",
    "worksheet_name": "Sheet1",
    "segments": [
        "Cash Flow Solutions",
        "Customer Financing Tools",
        "Equipment & Franchise Funding",
        "Healthcare & Practice Loans",
        "SBA & Business Expansion Loans",
        "Commercial Real Estate Loans",
        "Unsecured Business Credit",
        "Meet Our Founder"
    ]
}

# ----------------- AUTH ----------------- #
def write_credentials_from_env():
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise RuntimeError("GOOGLE_CREDENTIALS_BASE64 environment variable not found.")        
    creds_path = os.path.abspath("credentials.json")
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(encoded))
    return creds_path

@st.cache_resource
def get_gsheets_client() -> gspread.Client:
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = write_credentials_from_env()
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {str(e)}")
        return None

# ----------------- VALIDATION ----------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ----------------- MAIN APP ----------------- #
def main():
    st.set_page_config(page_title="Interest Form", page_icon="📋")
    st.title("Tell Us What You're Interested In")

    if 'submitted' not in st.session_state:
        st.session_state.submitted = False

    if st.session_state.submitted:
        st.success("✅ Thanks! You're now on the list.")

    with st.form("interest_form"):
        name = st.text_input("Your Name", max_chars=100)
        email = st.text_input("Your Email", max_chars=100)
        segment = st.selectbox("What would you like to hear about?", CONFIG["segments"])
        submit_button = st.form_submit_button("Submit")

    if submit_button:
        if not name.strip():
            st.error("Please provide your name")
            return
        if not is_valid_email(email):
            st.error("Please provide a valid email address")
            return

        client = get_gsheets_client()
        if client:
            try:
                spreadsheet = client.open(CONFIG["sheet_name"])
                sheet = spreadsheet.worksheet(CONFIG["worksheet_name"])

                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                sheet.append_row([
                    name.strip(),
                    email.strip().lower(),
                    segment,
                    "", "",  # Last_Email_Sent, Next_Step_Date
                    timestamp,
                    ""       # Notes
                ])

                st.session_state.submitted = True

            except Exception as e:
                st.error(f"Failed to save data: {str(e)}")
        else:
            st.error("Cannot connect to database. Please try again later.")

if __name__ == "__main__":
    main()
