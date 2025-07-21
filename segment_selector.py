import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import base64
import logging
import yaml
from typing import Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import re

# -------------------- LOGGING SETUP -------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("segment_updater.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- CONFIGURATION -------------------- #
class Config:
    def __init__(self):
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            self.sheet_name = cfg["sheets"]["name"]
            self.worksheet_name = cfg["sheets"]["worksheet"]
            self.retry_attempts = cfg.get("sheets", {}).get("retry_attempts", 3)
            self.retry_delay = cfg.get("sheets", {}).get("retry_delay", 5)
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

# -------------------- VALIDATION -------------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def is_valid_segment(segment: str) -> bool:
    return bool(segment and isinstance(segment, str) and segment.strip())

# -------------------- GOOGLE SHEETS CLIENT -------------------- #
class SheetClient:
    def __init__(self, config: Config):
        self.config = config
        self.scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        self.client = self._initialize_client()
        self.sheet = self._get_worksheet()

    def _initialize_client(self) -> Optional[gspread.Client]:
        try:
            encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
            if not encoded:
                raise ValueError("Missing GOOGLE_CREDENTIALS_BASE64 in environment")
            creds_path = os.path.abspath("credentials.json")
            with open(creds_path, "wb") as f:
                f.write(base64.b64decode(encoded))
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, self.scope)
            return gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            return None

    def _get_worksheet(self) -> Optional[gspread.Worksheet]:
        if not self.client:
            return None
        try:
            return self.client.open(self.config.sheet_name).worksheet(self.config.worksheet_name)
        except Exception as e:
            logger.error(f"Failed to access worksheet: {e}")
            return None

    def get_all_records(self) -> list:
        if not self.sheet:
            return []
        try:
            return self.sheet.get_all_records()
        except Exception as e:
            logger.error(f"Failed to fetch records: {e}")
            return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry_error_callback=lambda retry_state: None
    )
    def update_cell(self, row: int, col: int, value: str):
        if not self.sheet:
            return
        try:
            self.sheet.update_cell(row, col, value)
            logger.debug(f"Updated cell ({row}, {col}) with value: {value}")
        except Exception as e:
            logger.error(f"Failed to update cell ({row}, {col}): {e}")
            raise

# -------------------- SEGMENT MANAGER -------------------- #
class SegmentManager:
    def __init__(self, config: Config):
        self.config = config
        self.sheet_client = SheetClient(config)
        self.today = datetime.now().strftime("%Y-%m-%d")

    def handle_segment_selection(self, email: str, segment: str) -> bool:
        if not self.sheet_client.sheet:
            logger.error("Google Sheets client not available")
            return False

        if not is_valid_email(email):
            logger.warning(f"Invalid email address: {email}")
            return False

        if not is_valid_segment(segment):
            logger.warning(f"Invalid segment: {segment}")
            return False

        email = email.strip().lower()
        segment = segment.strip()

        try:
            data = self.sheet_client.get_all_records()
            for idx, row in enumerate(data, start=2):  # start=2 to match sheet row index
                row_email = row.get("Email", "").strip().lower()
                row_segment = row.get("Segment", "").strip()

                if row_email == email and row_segment == "Pending Segment Selection":
                    self.sheet_client.update_cell(idx, 3, segment)  # Segment
                    self.sheet_client.update_cell(idx, 4, "")       # Last_Email_Sent
                    self.sheet_client.update_cell(idx, 5, self.today)  # Next_Step_Date
                    logger.info(f"✅ Successfully updated segment for {email} to {segment}")
                    return True

            logger.warning(f"⚠️ No matching email with 'Pending Segment Selection' found for {email}")
            return False

        except Exception as e:
            logger.error(f"❌ Failed to process segment update for {email}: {e}")
            return False
