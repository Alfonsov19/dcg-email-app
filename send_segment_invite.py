import os
import base64
import logging
from typing import List
from urllib.parse import quote_plus
import yaml
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from email.mime.text import MIMEText
import smtplib

# -------------------- LOGGING SETUP -------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("segment_invite.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- LOAD CONFIG -------------------- #
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

config = load_config()
sheet_name = config["sheets"]["name"]
worksheet_name = config["sheets"]["worksheet"]
segments = config["app"]["segments"]
sender_email = config["email"]["sender_email"]
app_password = config["email"]["app_password"]

# -------------------- GOOGLE SHEETS -------------------- #
def init_gspread_client():
    creds_path = "credentials.json"
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise EnvironmentError("Missing GOOGLE_CREDENTIALS_BASE64")
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(encoded))
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    return client.open(sheet_name).worksheet(worksheet_name)

# -------------------- EMAIL SENDER -------------------- #
def send_email(to: str, subject: str, html_content: str):
    msg = MIMEText(html_content, "html")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.send_message(msg)
        logger.info(f"✅ Sent email to {to}")
    except Exception as e:
        logger.error(f"❌ Failed to send email to {to}: {e}")

# -------------------- BUILD EMAIL HTML -------------------- #
def build_segment_email(recipient_email: str) -> str:
    encoded_email = quote_plus(recipient_email)
    links = [
        f"<li><a href='https://dcg-email-app.onrender.com/?email={encoded_email}&segment={quote_plus(segment)}'>{segment}</a></li>"
        for segment in segments
    ]
    html_links = "\n".join(links)
    return f"""
    <html>
        <body>
            <p>Hi there 👋,</p>
            <p>Please select the financial area you're most interested in:</p>
            <ul>
                {html_links}
            </ul>
            <p>Once you click, we’ll send you personalized info and guidance to match!</p>
            <p>– The Doriscar Capital Group Team</p>
        </body>
    </html>
    """

# -------------------- MAIN FUNCTION -------------------- #
def main():
    sheet = init_gspread_client()
    data = sheet.get_all_records()

    for idx, row in enumerate(data, start=2):
        email = row.get("Email", "").strip()
        segment = row.get("Segment", "").strip().lower()

        if segment == "pending segment selection":
            logger.info(f"📨 Sending invite to: {email}")
            html = build_segment_email(email)
            send_email(email, "Welcome to Doriscar Capital – Choose Your Path", html)

if __name__ == "__main__":
    main()
