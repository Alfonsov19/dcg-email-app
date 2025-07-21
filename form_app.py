import streamlit as st
import os
import base64
from datetime import datetime, timedelta
from urllib.parse import unquote
import logging
import yaml
import re
import string

from typing import Optional, List
from segment_updater import Config as SegmentConfig, SegmentManager, SheetClient
from send_scheduled_emails import EmailSender, EmailSequenceManager
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# -------------------- LOGGING SETUP -------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("streamlit_app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- CONFIGURATION -------------------- #
class AppConfig:
    def __init__(self):
        config_path = os.getenv("CONFIG_PATH", "config.yaml")
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            self.page_title = cfg.get("app", {}).get("page_title", "Tell Us What You're Interested In")
            self.segments = cfg.get("app", {}).get("segments", [])
        except Exception as e:
            logger.error(f"Failed to load application configuration: {e}")
            raise

# -------------------- VALIDATION -------------------- #
def is_valid_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def smart_capitalize(s: str) -> str:
    return string.capwords(s.replace(".", " ").replace("_", " ")).replace(" ", "")

# -------------------- UI MANAGER -------------------- #
class UIManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.setup_page()

    def setup_page(self):
        st.set_page_config(page_title=self.config.page_title, layout="centered")
        st.title("🧭 Tell Us What You're Interested In")
        st.markdown("Please select your preferred segment below:")
        st.markdown("---")

    def display_error(self, message: str):
        st.error(f"❌ {message}")
        logger.error(message)

    def display_success(self, message: str):
        st.success(f"🎉 {message}")
        logger.info(message)

# -------------------- SEGMENT HANDLER -------------------- #
class SegmentHandler:
    def __init__(self, segment_config: SegmentConfig):
        self.segment_manager = SegmentManager(segment_config)
        self.email_sender = EmailSender(segment_config)
        self.sequence_manager = EmailSequenceManager(segment_config)
        self.sheet = SheetClient(segment_config).sheet

    def update_segment_and_send_email(self, email: str, segment: str) -> bool:
        try:
            if not is_valid_email(email):
                logger.warning(f"Invalid email address: {email}")
                return False

            if not segment or not isinstance(segment, str):
                logger.warning(f"Invalid segment: {segment}")
                return False

            success = self.segment_manager.handle_segment_selection(email, segment)
            if not success:
                return False

            sequence = self.sequence_manager.load_sequence(segment)
            if not sequence or not isinstance(sequence, list):
                logger.warning(f"Missing or invalid email sequence for segment: {segment}")
                return False

            first_email = sequence[0]
            if "subject" not in first_email or "body" not in first_email:
                logger.warning(f"Invalid structure in first email of sequence for segment: {segment}")
                return False

            # Extract name from email
            name = smart_capitalize(email.split("@")[0])

            # Send Week 1 email
            subject = first_email["subject"]
            body = first_email["body"].replace("{name}", name or "there")
            email_sent = self.email_sender.send_email(subject, body, email)

            if not email_sent:
                logger.error(f"Email sending failed for: {email}")
                return False

            # Update Google Sheet: Last_Email_Sent and Next_Step_Date
            records = self.sheet.get_all_records()
            for idx, row in enumerate(records):
                if row.get("Email", "").strip().lower() == email.lower():
                    row_index = idx + 2
                    self.sheet.update_cell(row_index, 4, "Week 1")
                    self.sheet.update_cell(row_index, 5, (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"))
                    break

            return True

        except Exception as e:
            logger.error(f"Failed to process segment update and email for {email}: {e}")
            return False

# -------------------- MAIN APPLICATION -------------------- #
def main():
    try:
        segment_config = SegmentConfig()
        app_config = AppConfig()
        ui = UIManager(app_config)
        handler = SegmentHandler(segment_config)

        # Get email from query params
        query_params = st.query_params
        email = unquote(query_params.get("email", [""])[0]).strip()

        if not email:
            ui.display_error("Email not found in URL query string.")
            st.stop()

        if not is_valid_email(email):
            ui.display_error("Invalid email format in URL.")
            st.stop()

        selected_segment = st.radio("Select your interest:", app_config.segments)

        if st.button("✅ Confirm Selection"):
            success = handler.update_segment_and_send_email(email, selected_segment)
            if success:
                ui.display_success(f"You're now subscribed to **{selected_segment}** updates. Watch your inbox!")
            else:
                ui.display_error("No matching email with 'Pending Segment Selection' found in the sheet.")

    except Exception as e:
        logger.critical(f"Application failed: {e}")
        st.error(f"An unexpected error occurred: {e}")

# -------------------- RUN -------------------- #
if __name__ == "__main__":
    main()
