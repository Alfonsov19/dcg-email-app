import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import smtplib
from email.message import EmailMessage
import os
import base64

# -------------------- CONFIG -------------------- #
SENDER_EMAIL = "dcgcapital3@gmail.com"
APP_PASSWORD = "fykn tdfm qafy rqks"  # Gmail app password
EMAIL_SEQUENCE_FOLDER = "email_sequences"
SHEET_NAME = "dcg_contacts"
WORKSHEET_NAME = "Sheet1"

# -------------------- CREDENTIALS FROM ENV -------------------- #
def write_credentials_from_env():
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise RuntimeError("GOOGLE_CREDENTIALS_BASE64 environment variable not found.")
    creds_path = os.path.abspath("credentials.json")
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(encoded))
    return creds_path

# -------------------- LOAD SHEET -------------------- #
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_path = write_credentials_from_env()
creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
client = gspread.authorize(creds)
sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)
rows = sheet.get_all_records()
today = datetime.now().strftime("%Y-%m-%d")

# -------------------- EMAIL SENDER -------------------- #
def send_email(subject, body, recipient_email):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SENDER_EMAIL
    msg["To"] = recipient_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(SENDER_EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        return False

# -------------------- LOAD EMAIL SEQUENCE -------------------- #
def load_email_sequence(segment_name):
    filename = os.path.join(
        EMAIL_SEQUENCE_FOLDER,
        f"{segment_name.strip().lower().replace(' ', '_')}.json"
    )
    if not os.path.exists(filename):
        print(f"⚠️ No sequence found for: {segment_name}")
        return []
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

# -------------------- CTA LOOP MESSAGE -------------------- #
CTA_MESSAGE = """Hi {name},

We noticed you haven't scheduled your free strategy call yet.

We're here to help you move forward with funding that fits your vision.

📅 Book your call now: https://calendly.com/dcgcapital3/30min

Looking forward to helping you grow,  
Doriscar Capital Group
"""

# -------------------- MAIN LOOP -------------------- #
for idx, row in enumerate(rows):
    next_step_date = row.get("Next_Step_Date", "").strip()
    segment = row.get("Segment", "").strip()
    email = row.get("Email", "").strip()
    name = row.get("Name", "").strip()
    last_email = row.get("Last_Email_Sent", "").strip()

    if not email or not segment or segment == "Pending Segment Selection":
        continue
    if next_step_date != today:
        continue
    if last_email == "CTA Loop":
        continue

    sequence = load_email_sequence(segment)
    if not sequence:
        continue

    # Determine next email index
    if not last_email:
        email_index = 0
    elif "Week" in last_email:
        try:
            email_index = int(last_email.replace("Week ", ""))
        except ValueError:
            email_index = 0
    else:
        email_index = 0

    if email_index < len(sequence):
        email_data = sequence[email_index]
        subject = email_data["subject"]
        body = email_data["body"].replace("{name}", name if name else "there")
        sent = send_email(subject, body, email)

        if sent:
            sheet.update_cell(idx + 2, 4, f"Week {email_index + 1}")  # Last_Email_Sent
            next_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            sheet.update_cell(idx + 2, 5, next_date)  # Next_Step_Date

            with open("email_log.txt", "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] Sent '{subject}' to {email} (Week {email_index + 1})\n")
    else:
        # Sequence complete – begin CTA loop
        subject = "👋 Still Thinking It Over? Let's Talk"
        body = CTA_MESSAGE.replace("{name}", name if name else "there")
        sent = send_email(subject, body, email)

        if sent:
            sheet.update_cell(idx + 2, 4, "CTA Loop")
            next_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            sheet.update_cell(idx + 2, 5, next_date)
            with open("email_log.txt", "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] Sent CTA Loop email to {email}\n")
