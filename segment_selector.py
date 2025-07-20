import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import os
import base64
from send_scheduled_emails import send_email, load_email_sequence

CONFIG = {
    "sheet_name": "dcg_contacts",
    "worksheet_name": "Sheet1"
}

# -------------------- GOOGLE SHEETS AUTH -------------------- #
def get_gsheets_client():
    try:
        encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
        if not encoded:
            raise RuntimeError("Missing GOOGLE_CREDENTIALS_BASE64 in environment.")
        creds_path = os.path.abspath("credentials.json")
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(encoded))
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        return gspread.authorize(creds)
    except Exception as e:
        print(f"❌ Failed to connect to Google Sheets: {e}")
        return None

# -------------------- MAIN FUNCTION -------------------- #
def handle_segment_selection(email: str, segment: str):
    client = get_gsheets_client()
    if not client:
        print("❌ Google Sheets client not available.")
        return

    try:
        sheet = client.open(CONFIG["sheet_name"]).worksheet(CONFIG["worksheet_name"])
        data = sheet.get_all_records()
        email = email.strip().lower()

        for idx, row in enumerate(data, start=2):  # row index starts at 2 (1-based with headers)
            if row.get("Email", "").strip().lower() == email:
                # Update values
                today = datetime.now().strftime("%Y-%m-%d")
                next_week = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                sheet.update_cell(idx, 3, segment)        # Segment
                sheet.update_cell(idx, 4, "Week 1")       # Last_Email_Sent
                sheet.update_cell(idx, 5, next_week)      # Next_Step_Date

                # Send first email (Week 1)
                sequence = load_email_sequence(segment)
                if sequence:
                    first_email = sequence[0]
                    subject = first_email["subject"]
                    body = first_email["body"].replace("{name}", row["Name"])
                    send_email(subject, body, email)
                    print(f"✅ Sent Week 1 email to {email}")
                else:
                    print(f"⚠️ No email sequence found for segment '{segment}'")

                return

        print(f"⚠️ No matching email found for {email}")

    except Exception as e:
        print(f"❌ Failed to update Google Sheets or send email: {e}")
