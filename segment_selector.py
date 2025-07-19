import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
from urllib.parse import unquote

# -------------------- CONFIG -------------------- #
CONFIG = {
    "sheet_name": "dcg_contacts",
    "worksheet_name": "Sheet1"
}

# -------------------- AUTH -------------------- #
@st.cache_resource
def get_gsheets_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_path = os.path.abspath("credentials.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"❌ Failed to connect to Google Sheets: {e}")
        return None

# -------------------- MAIN -------------------- #
def main():
    st.set_page_config(page_title="Thanks for Choosing!", page_icon="✅")
    st.title("✅ You're All Set!")

    # Get email and segment from URL query params
    query_params = st.query_params
    email = unquote(query_params.get("email", ""))
    segment = unquote(query_params.get("segment", ""))

    if not email or not segment:
        st.error("Missing email or segment in the URL.")
        return

    st.success(f"🎯 Thanks, {email}! You’ve selected: **{segment}**.")
    st.write("We’ve saved your preferences and will follow up with helpful insights!")

    # Update Google Sheets
    client = get_gsheets_client()
    if client:
        try:
            sheet = client.open(CONFIG["sheet_name"]).worksheet(CONFIG["worksheet_name"])
            data = sheet.get_all_records()
            for idx, row in enumerate(data):
                if row["Email"].strip().lower() == email.strip().lower():
                    sheet.update_cell(idx + 2, 3, segment)  # Segment
                    sheet.update_cell(idx + 2, 4, "")        # Last_Email_Sent
                    sheet.update_cell(idx + 2, 5, (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))  # Next_Step_Date
                    break
        except Exception as e:
            st.error(f"❌ Failed to update Google Sheets: {e}")

if __name__ == "__main__":
    main()
