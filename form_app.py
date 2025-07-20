import streamlit as st
import gspread
import os
import base64
from oauth2client.service_account import ServiceAccountCredentials
from urllib.parse import unquote


# ----------------- AUTH SETUP ----------------- #
def write_credentials_from_env():
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise RuntimeError("GOOGLE_CREDENTIALS_BASE64 is not set.")
    creds_path = os.path.abspath("credentials.json")
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(encoded))
    return creds_path

def get_gsheet_client():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_path = write_credentials_from_env()
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)


# ----------------- SHEET CONFIG ----------------- #
SHEET_NAME = "dcg_contacts"
WORKSHEET_NAME = "Sheet1"


# ----------------- UPDATE FUNCTION ----------------- #
def update_segment(email, segment):
    client = get_gsheet_client()
    sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
    all_rows = sheet.get_all_records()
    
    for idx, row in enumerate(all_rows):
        if row.get("Email", "").strip().lower() == email.lower():
            sheet.update_cell(idx + 2, 3, segment)  # Column C = Segment
            return True
    return False


# ----------------- UI LOGIC ----------------- #
st.set_page_config(page_title="Tell Us What You're Interested In", layout="centered")
st.title("🧭 Tell Us What You're Interested In")
st.markdown("Please select your preferred segment below:")

# Grab email from query param
query_params = st.experimental_get_query_params()
email = unquote(query_params.get("email", [""])[0])

segments = [
    "Cash Flow Solutions",
    "Customer Financing Tools",
    "Equipment & Franchise Funding",
    "Healthcare & Practice Loans",
    "SBA & Business Expansion Loans",
    "Commercial Real Estate Loans",
    "Unsecured Business Credit",
    "Meet Our Founder"
]

selected_segment = st.radio("Segments", segments)
if st.button("✅ Confirm Selection"):
    if email:
        success = update_segment(email, selected_segment)
        if success:
            st.success(f"🎉 You're now subscribed to **{selected_segment}** updates. Watch your inbox!")
        else:
            st.error("⚠️ Email not found in database.")
    else:
        st.warning("⚠️ No email detected from the URL.")
