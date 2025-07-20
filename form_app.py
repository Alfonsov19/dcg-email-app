import streamlit as st
import gspread
import os
import base64
from urllib.parse import unquote
from oauth2client.service_account import ServiceAccountCredentials

# ---------------- Google Sheets Auth ---------------- #
def write_credentials_from_env():
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise RuntimeError("Missing GOOGLE_CREDENTIALS_BASE64 env variable.")
    with open("credentials.json", "wb") as f:
        f.write(base64.b64decode(encoded))
    return "credentials.json"

def get_gsheet_client():
    creds_path = write_credentials_from_env()
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)

# ---------------- Update Sheet Function ---------------- #
def update_segment(email, segment):
    client = get_gsheet_client()
    sheet = client.open("dcg_contacts").worksheet("Sheet1")
    data = sheet.get_all_records()

    for i, row in enumerate(data):
        if row.get("Email", "").strip().lower() == email.strip().lower():
            sheet.update_cell(i + 2, 3, segment)  # Row offset +2, Column C = 3
            return True
    return False

# ---------------- Streamlit UI ---------------- #
st.set_page_config(page_title="Tell Us What You're Interested In", layout="centered")
st.title("🧭 Tell Us What You're Interested In")
st.markdown("Please select your preferred segment below:")

query_params = st.query_params
email = unquote(query_params.get("email", "")).strip()

if not email:
    st.error("❌ Email not found in URL query string.")
    st.stop()

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
    success = update_segment(email, selected_segment)
    if success:
        st.success(f"🎉 You're now subscribed to **{selected_segment}** updates. Watch your inbox!")
    else:
        st.error("⚠️ Could not find your email in the sheet to update.")
