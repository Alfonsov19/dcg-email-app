import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import re
import os
import base64
from urllib.parse import unquote
import smtplib
from email.message import EmailMessage

# ----------------- CONFIG ----------------- #
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
    "sender_email": "dcgcapital3@gmail.com",
    "app_password": "fykn tdfm qafy rqks",
    "base_url": "https://dcg-email-app.onrender.com"
}

# ----------------- CREDENTIALS ----------------- #
def write_credentials_from_env():
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise RuntimeError("GOOGLE_CREDENTIALS_BASE64 environment variable not found.")
    creds_path = os.path.abspath("credentials.json")
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(encoded))
    return creds_path

@st.cache_resource
def get_gsheets_client() -> gspread.Client:
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = write_credentials_from_env()
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Failed to connect to Google Sheets: {str(e)}")
        return None

# ----------------- EMAIL UTILS ----------------- #
def send_email(subject, body, recipient_email):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = CONFIG["sender_email"]
    msg["To"] = recipient_email
    msg.set_content(body)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(CONFIG["sender_email"], CONFIG["app_password"])
            smtp.send_message(msg)
        return True
    except Exception as e:
        print(f"❌ Failed to send email to {recipient_email}: {e}")
        return False

def build_welcome_email(name, email):
    segments = {
        "Cash Flow Solutions": "💸",
        "Customer Financing Tools": "🧾",
        "Equipment & Franchise Funding": "🛠️",
        "Healthcare & Practice Loans": "🩺",
        "SBA & Business Expansion Loans": "🚀",
        "Commercial Real Estate Loans": "🏢",
        "Unsecured Business Credit": "💳",
        "Meet Our Founder": "👨‍⚕️"
    }

    links = "\n".join([
        f"{icon} {title}: {CONFIG['base_url']}?email={email}&segment={title.replace(' ', '%20')}"
        for title, icon in segments.items()
    ])

    subject = "Welcome to Doriscar Capital Group"
    body = f"""Hi {name},

Thanks for connecting with Doriscar Capital Group!

We help entrepreneurs and business owners access the capital they need to grow — from working capital and equipment financing to SBA loans and real estate funding.

Let us know what you're most interested in. Just click one:

{links}

Once you click, we’ll personalize everything we send you moving forward.

Cheers,  
Doriscar Capital Group
"""
    return subject, body

# ----------------- EMAIL VALIDATION ----------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# ----------------- URL PARAM HANDLER ----------------- #
query_params = st.query_params
email_param = query_params.get("email", [None])[0]
segment_param = query_params.get("segment", [None])[0]

if email_param:
    st.set_page_config(page_title="Select Your Segment", page_icon="🧭")
    st.title("🧭 Tell Us What You're Interested In")

    email_param = unquote(email_param).strip().lower()
    segment_param = unquote(segment_param).strip() if segment_param else CONFIG["segments"][0]

    selected = st.radio("Please select a segment:", CONFIG["segments"],
                        index=CONFIG["segments"].index(segment_param) if segment_param in CONFIG["segments"] else 0)

    if st.button("✅ Confirm Selection"):
        import segment_selector  # Make sure this file exists
        try:
            segment_selector.handle_segment_selection(email_param, selected)
            st.success(f"You’ve been subscribed to **{selected}**! 🎉 Watch your inbox.")
        except Exception as e:
            st.error(f"Something went wrong: {e}")
    st.stop()

# ----------------- MAIN FORM (if no query params) ----------------- #
def main():
    st.set_page_config(page_title="Interest Form", page_icon="📋")
    st.title("📋 Tell Us What You're Interested In")

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
                    "", "",  # Last_Email_Sent, Next_Step_Date
                    timestamp,
                    ""       # Notes
                ])

                # Send welcome email
                subject, body = build_welcome_email(name.strip(), email.strip().lower())
                send_email(subject, body, email.strip().lower())

                st.session_state.submitted = True

            except Exception as e:
                st.error(f"Failed to save data: {str(e)}")
        else:
            st.error("Cannot connect to database. Please try again later.")

if __name__ == "__main__":
    main()
