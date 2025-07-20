import streamlit as st
import gspread
import os
import base64
from datetime import datetime
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
    if not segment:
        return False

    client = get_gsheet_client()
    sheet = client.open("dcg_contacts").worksheet("Sheet1")
    data = sheet.get_all_records()

    updated = False
    for i, row in enumerate(data):
        if (
            row.get("Email", "").strip().lower() == email.strip().lower()
            and row.get("Segment", "").strip() == "Pending Segment Selection"
        ):
            # Update Segment column (C)
            sheet.update_cell(i + 2, 3, segment)
            # Update Timestamp column (F)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            sheet.update_cell(i + 2, 6, timestamp)
            updated = True
    return updated

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
        st.error("⚠️ No matching email with 'Pending Segment Selection' found in the sheet.")
