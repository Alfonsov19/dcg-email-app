import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os
import re

# -------------------- CONFIG -------------------- #
CONFIG = {
    "sheet_name": "dcg_contacts",
    "worksheet_name": "Sheet1",
    "segments": [
        "Business Financing",
        "Credit Building",
        "Financial Education",
        "Referral & Partnership Opportunities"
    ],
    "sender_email": "your_email@gmail.com",              # ✅ Your Gmail
    "app_password": "your_app_password",                 # ✅ Your Gmail App Password
    "base_url": "https://yourdomain.com/select"          # ✅ Replace with your actual URL
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
        st.error(f"Failed to connect to Google Sheets: {e}")
        return None

# -------------------- VALIDATION -------------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

# -------------------- EMAIL FUNCTION -------------------- #
def send_segment_invite(name, email):
    try:
        segment_links = "\n".join([
            f"📈 Business Financing: {CONFIG['base_url']}?email={email}&segment=Business+Financing",
            f"💳 Credit Building: {CONFIG['base_url']}?email={email}&segment=Credit+Building",
            f"📚 Financial Education: {CONFIG['base_url']}?email={email}&segment=Financial+Education",
            f"🤝 Referral Opportunities: {CONFIG['base_url']}?email={email}&segment=Referral+Partnership"
        ])

        body = f"""Hi {name},

Thanks for connecting with us!

We help ambitious individuals and business owners with:

👉 Business Financing  
👉 Credit Building  
👉 Financial Education  
👉 Referral & Partnership Opportunities

Let us know what you’d like to learn more about. Just click one:

{segment_links}

Once you click, we’ll make sure you only receive what’s most relevant to you.

Best regards,  
Doriscar Capital Group
"""

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = "Welcome to Doriscar Capital Group!"
        msg['From'] = CONFIG['sender_email']
        msg['To'] = email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(CONFIG['sender_email'], CONFIG['app_password'])
            smtp.send_message(msg)

        return True
    except Exception as e:
        st.error(f"❌ Failed to send welcome email: {e}")
        return False

# -------------------- STREAMLIT APP -------------------- #
def main():
    st.set_page_config(page_title="Send Welcome Email", page_icon="📧")
    st.title("📧 Send Welcome Email with Segment Options")

    with st.form("segment_invite_form"):
        name = st.text_input("Recipient's Name")
        email = st.text_input("Recipient's Email")
        submit = st.form_submit_button("Send Email + Save")

    if submit:
        if not name.strip():
            st.error("Please enter a name.")
            return
        if not is_valid_email(email):
            st.error("Please enter a valid email.")
            return

        sent = send_segment_invite(name.strip(), email.strip())

        if sent:
            # Save to Google Sheets
            client = get_gsheets_client()
            if client:
                try:
                    sheet = client.open(CONFIG["sheet_name"]).worksheet(CONFIG["worksheet_name"])
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([
                        name.strip(),
                        email.strip().lower(),
                        "Pending Segment Selection",  # Segment not yet selected
                        "", "",  # Last_Email_Sent, Next_Step_Date
                        timestamp,
                        ""       # Notes
                    ])
                    st.success("✅ Email sent and data saved to Google Sheets.")
                except Exception as e:
                    st.error(f"Failed to save to Google Sheets: {e}")
            else:
                st.error("Could not connect to Google Sheets.")

if __name__ == "__main__":
    main()