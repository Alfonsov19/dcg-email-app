import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime, timedelta
import json
import smtplib
from email.message import EmailMessage
import os
import base64
import logging
import re
from typing import Dict, List, Optional
import yaml
from tenacity import retry, stop_after_attempt, wait_exponential

# -------------------- CONFIGURATION -------------------- #
class Config:
    def __init__(self):
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        
        self.sender_email = cfg["email"]["sender_email"]
        self.app_password = cfg["email"]["app_password"]
        self.email_sequence_folder = cfg["email"]["sequence_folder"]
        self.sheet_name = cfg["sheets"]["name"]
        self.worksheet_name = cfg["sheets"]["worksheet"]
        self.retry_attempts = cfg.get("email", {}).get("retry_attempts", 3)
        self.retry_delay = cfg.get("email", {}).get("retry_delay", 5)

# -------------------- LOGGING SETUP -------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("email_campaign.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- EMAIL VALIDATION -------------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

# -------------------- CREDENTIALS MANAGER -------------------- #
def setup_credentials() -> str:
    try:
        encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
        if not encoded:
            raise ValueError("GOOGLE_CREDENTIALS_BASE64 environment variable not found")
        
        creds_path = os.path.abspath("credentials.json")
        with open(creds_path, "wb") as f:
            f.write(base64.b64decode(encoded))
        return creds_path
    except Exception as e:
        logger.error(f"Failed to setup credentials: {e}")
        raise

# -------------------- GOOGLE SHEETS CLIENT -------------------- #
class SheetClient:
    def __init__(self, config: Config):
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.config = config
        self.client = self._initialize_client()
        self.sheet = self._get_worksheet()

    def _initialize_client(self):
        creds_path = setup_credentials()
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, self.scope)
        return gspread.authorize(creds)

    def _get_worksheet(self):
        return self.client.open(self.config.sheet_name).worksheet(self.config.worksheet_name)

    def get_all_records(self) -> List[Dict]:
        return self.sheet.get_all_records()

    def update_cell(self, row: int, col: int, value: str):
        try:
            self.sheet.update_cell(row, col, value)
        except Exception as e:
            logger.error(f"Failed to update cell ({row}, {col}): {e}")

# -------------------- EMAIL SENDER -------------------- #
class EmailSender:
    def __init__(self, config: Config):
        self.config = config

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: False
    )
    def send_email(self, subject: str, body: str, recipient_email: str) -> bool:
        if not is_valid_email(recipient_email):
            logger.warning(f"Invalid email address: {recipient_email}")
            return False

        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.config.sender_email
        msg["To"] = recipient_email
        msg.set_content(body)

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
                smtp.login(self.config.sender_email, self.config.app_password)
                smtp.send_message(msg)
            logger.info(f"Successfully sent email to {recipient_email}: {subject}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_email}: {e}")
            return False

# -------------------- EMAIL SEQUENCE MANAGER -------------------- #
class EmailSequenceManager:
    def __init__(self, config: Config):
        self.config = config
        self.cta_message = """Hi {name},

We noticed you haven't scheduled your free strategy call yet.

We're here to help you move forward with funding that fits your vision.

📅 Book your call now: https://calendly.com/dcgcapital3/30min

Looking forward to helping you grow,  
Doriscar Capital Group
"""

    def load_sequence(self, segment_name: str) -> List[Dict]:
        filename = os.path.join(
            self.config.email_sequence_folder,
            f"{segment_name.strip().lower().replace(' ', '_')}.json"
        )
        try:
            if not os.path.exists(filename):
                logger.warning(f"No sequence found for segment: {segment_name}")
                return []
            with open(filename, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load sequence {filename}: {e}")
            return []

    def get_cta_message(self, name: str) -> tuple:
        return (
            "👋 Still Thinking It Over? Let's Talk",
            self.cta_message.replace("{name}", name if name else "there")
        )

# -------------------- MAIN CAMPAIGN MANAGER -------------------- #
class CampaignManager:
    def __init__(self, config: Config):
        self.config = config
        self.sheet_client = SheetClient(config)
        self.email_sender = EmailSender(config)
        self.sequence_manager = EmailSequenceManager(config)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def process_contacts(self):
        rows = self.sheet_client.get_all_records()
        
        for idx, row in enumerate(rows):
            try:
                self._process_contact(idx, row)
            except Exception as e:
                logger.error(f"Error processing contact at row {idx + 2}: {e}")

    def _process_contact(self, idx: int, row: Dict):
        email = row.get("Email", "").strip()
        segment = row.get("Segment", "").strip()
        name = row.get("Name", "").strip()
        next_step_date = row.get("Next_Step_Date", "").strip()
        last_email = row.get("Last_Email_Sent", "").strip()

        # Skip invalid or incomplete records
        if not email or not segment or segment == "Pending Segment Selection":
            logger.debug(f"Skipping invalid record: {email}, {segment}")
            return
        if next_step_date != self.today:
            return
        if last_email == "CTA Loop":
            return

        sequence = self.sequence_manager.load_sequence(segment)
        if not sequence:
            return

        # Determine email index
        email_index = self._get_email_index(last_email, sequence)

        # Process email or CTA loop
        if email_index < len(sequence):
            self._send_sequence_email(idx, email, name, sequence, email_index)
        else:
            self._send_cta_email(idx, email, name)

    def _get_email_index(self, last_email: str, sequence: List[Dict]) -> int:
        if not last_email:
            return 0
        if "Week" in last_email:
            try:
                return int(last_email.replace("Week ", ""))
            except ValueError:
                logger.warning(f"Invalid last_email format: {last_email}")
                return 0
        return 0

    def _send_sequence_email(self, idx: int, email: str, name: str, sequence: List[Dict], email_index: int):
        email_data = sequence[email_index]
        subject = email_data["subject"]
        body = email_data["body"].replace("{name}", name if name else "there")
        
        if self.email_sender.send_email(subject, body, email):
            self.sheet_client.update_cell(idx + 2, 4, f"Week {email_index + 1}")
            next_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            self.sheet_client.update_cell(idx + 2, 5, next_date)

    def _send_cta_email(self, idx: int, email: str, name: str):
        subject, body = self.sequence_manager.get_cta_message(name)
        if self.email_sender.send_email(subject, body, email):
            self.sheet_client.update_cell(idx + 2, 4, "CTA Loop")
            next_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            self.sheet_client.update_cell(idx + 2, 5, next_date)

# -------------------- MANUAL TRIGGER: send_segment_email() -------------------- #
def send_segment_email(email: str, segment: str) -> bool:
    """
    Sends the first email in the selected segment sequence and updates sheet tracking.
    """
    try:
        config = Config()
        sheet_client = SheetClient(config)
        email_sender = EmailSender(config)
        sequence_manager = EmailSequenceManager(config)

        # Get the contact row
        records = sheet_client.get_all_records()
        for idx, row in enumerate(records):
            if row["Email"].strip().lower() == email.strip().lower():
                name = row.get("Name", "there")
                break
        else:
            logger.warning(f"Email {email} not found in sheet during segment email send.")
            return False

        sequence = sequence_manager.load_sequence(segment)
        if not sequence:
            logger.warning(f"No sequence found for segment {segment}")
            return False

        first_email = sequence[0]
        subject = first_email["subject"]
        body = first_email["body"].replace("{name}", name)

        if email_sender.send_email(subject, body, email):
            row_index = idx + 2
            sheet_client.update_cell(row_index, 4, "Week 1")
            next_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
            sheet_client.update_cell(row_index, 5, next_date)
            logger.info(f"Segment email successfully sent and logged for {email}")
            return True
        return False
    except Exception as e:
        logger.error(f"Failed in send_segment_email for {email}: {e}")
        return False
