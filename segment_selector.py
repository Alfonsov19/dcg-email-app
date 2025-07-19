import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os

# -------------------- CONFIG -------------------- #
CONFIG = {
    "sheet_name": "dcg_contacts",
    "worksheet_name": "Sheet1"
}

# -------------------- AUTH -------------------- #
def get_gsheets_client():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_path = os.path.abspath("credentials.json")
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheets: {e}")
        return None

# -------------------- HANDLER FUNCTION -------------------- #
def handle_segment_selection(email: str, segment: str):
    """
    Tags the given email with the selected segment in Google Sheets,
    clears the last email sent, and schedules the next email.
    """
    client = get_gsheets_client()
    if not client:
        print("❌ Google Sheets client not available.")
        return

    try:
        sheet = client.open(CONFIG["sheet_name"]).worksheet(CONFIG["worksheet_name"])
        data = sheet.get_all_records()
        email = email.strip().lower()

        for idx, row in enumerate(data):
            if row.get("Email", "").strip().lower() == email:
                sheet.update_cell(idx + 2, 3, segment)  # Segment
                sheet.update_cell(idx + 2, 4, "")        # Last_Email_Sent
                sheet.update_cell(idx + 2, 5, (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))  # Next_Step_Date
                print(f"✅ Updated segment for {email} to '{segment}'")
                return

        print(f"⚠️ No matching email found for {email}")

    except Exception as e:
        print(f"❌ Failed to update Google Sheets: {e}")
