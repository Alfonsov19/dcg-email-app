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
        "Cash Flow Solutions",
        "Customer Financing Tools",
        "Equipment & Franchise Funding",
        "Healthcare & Practice Loans",
        "SBA & Business Expansion Loans",
        "Commercial Real Estate Loans",
        "Unsecured Business Credit",
        "Meet Our Founder"
    ],
    "sender_email": "dcgcapital3@gmail.com",  # ✅ Your Gmail
    "app_password": "fykn tdfm qafy rqks",     # ✅ Your Gmail App Password
    "base_url": "http://localhost:8501/select"  # 🔁 Replace with your deployed URL when ready
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

# -------------------- VALIDATION -------------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return bool(re.match(pattern, email))

# -------------------- EMAIL FUNCTION -------------------- #
def send_segment_invite(name, email):
    try:
        segment_links = "\n".join([
            f"💸 Cash Flow Solutions: {CONFIG['base_url']}?email={email}&segment=Cash+Flow+Solutions",
            f"🧾 Customer Financing Tools: {CONFIG['base_url']}?email={email}&segment=Customer+Financing+Tools",
            f"🛠️ Equipment & Franchise Funding: {CONFIG['base_url']}?email={email}&segment=Equipment+Franchise+Funding",
            f"🩺 Healthcare & Practice Loans: {CONFIG['base_url']}?email={email}&segment=Healthcare+Practice+Loans",
            f"🚀 SBA & Business Expansion Loans: {CONFIG['base_url']}?email={email}&segment=SBA+Business+Expansion+Loans",
            f"🏢 Commercial Real Estate Loans: {CONFIG['base_url']}?email={email}&segment=Commercial+Real+Estate+Loans",
            f"💳 Unsecured Business Credit: {CONFIG['base_url']}?email={email}&segment=Unsecured+Business+Credit",
            f"👨‍⚕️ Meet Our Founder: {CONFIG['base_url']}?email={email}&segment=Meet+Our+Founder"
        ])

        body = f"""Hi {name},

Thanks for connecting with Doriscar Capital Group!

We help entrepreneurs and business owners access the capital they need to grow — from working capital and equipment financing to SBA loans and real estate funding.

Let us know what you're most interested in. Just click one:

{segment_links}

Once you click, we’ll personalize everything we send you moving forward.

Cheers,  
Doriscar Capital Group
"""

        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = "🚀 Welcome! Choose What You Want to Learn About"
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
            client = get_gsheets_client()
            if client:
                try:
                    sheet = client.open(CONFIG["sheet_name"]).worksheet(CONFIG["worksheet_name"])
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    sheet.append_row([
                        name.strip(),
                        email.strip().lower(),
                        "Pending Segment Selection",  # Will be updated when link is clicked
                        "", "",  # Last_Email_Sent, Next_Step_Date
                        timestamp,
                        ""       # Notes
                    ])
                    st.success("✅ Email sent and data saved to Google Sheets.")
                except Exception as e:
                    st.error(f"❌ Failed to save to Google Sheets: {e}")
            else:
                st.error("❌ Could not connect to Google Sheets.")

if __name__ == "__main__":
    main()
