import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os
from email.message import EmailMessage
import smtplib

# ----------------- CONFIG ----------------- #
CONFIG = {
    "sheet_name": "dcg_contacts",
    "worksheet_name": "Sheet1",
    "segments": [
        "Business Financing",
        "Credit Building",
        "Financial Education",
        "Referral & Partnership Opportunities"
    ],
    "sender_email": "dcgcapital3@gmail.com",
    "app_password": "fykn tdfm qafy rqks"
}

# ----------------- EMAIL UTILS ----------------- #
def send_email(name, recipient_email, segment):
    subject = "Welcome to Doriscar Capital Group!"

    body = f"""
 Hi {name},

Thank you for connecting with Doriscar Capital Group.

Since you're interested in {segment}, we’ll send you valuable content and updates tailored to that area.

Stay tuned and feel free to reach out if you have any questions.

Best regards,  
Doriscar Capital Group Team
    """

    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg['Subject'] = subject
        msg['From'] = CONFIG["sender_email"]
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(CONFIG["sender_email"], CONFIG["app_password"])
            smtp.send_message(msg)

        return True
    except Exception as e:
        st.warning(f"❌ Email not sent: {e}")
        return False

# ----------------- AUTH ----------------- #
@st.cache_resource
def get_gsheets_client() -> gspread.Client:
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = os.path.abspath("credentials.json")
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"credentials.json not found at {creds_path}")

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
                    "", "",
                    timestamp,
                    ""
                ])

                # ✅ Send Welcome Email
                if send_email(name.strip(), email.strip().lower(), segment):
                    st.success("Email sent successfully.")
                else:
                    st.warning("Submission saved, but email not delivered.")

                st.session_state.submitted = True

            except Exception as e:
                st.error(f"Failed to save data: {str(e)}")
        else:
            st.error("Cannot connect to database. Please try again later.")

if __name__ == "__main__":
    main()
