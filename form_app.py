import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import base64
from urllib.parse import unquote
import segment_selector

# ----------------- CONFIG ----------------- #
CONFIG = {
    "segments": [
        "Cash Flow Solutions",
        "Customer Financing Tools",
        "Equipment & Franchise Funding",
        "Healthcare & Practice Loans",
        "SBA & Business Expansion Loans",
        "Commercial Real Estate Loans",
        "Unsecured Business Credit",
        "Meet Our Founder"
    ]
}

# ----------------- ENV-BASED CREDENTIALS ----------------- #
def write_credentials_from_env():
    encoded = os.getenv("GOOGLE_CREDENTIALS_BASE64")
    if not encoded:
        raise RuntimeError("GOOGLE_CREDENTIALS_BASE64 environment variable not found.")
    creds_path = os.path.abspath("credentials.json")
    with open(creds_path, "wb") as f:
        f.write(base64.b64decode(encoded))
    return creds_path

# ----------------- IF EMAIL + SEGMENT PRESENT ----------------- #
query_params = st.query_params
email_param = query_params.get("email", [None])[0]
segment_param = query_params.get("segment", [None])[0]

if email_param:
    st.set_page_config(page_title="Select Your Segment", page_icon="🧭")
    st.title("🧭 Tell Us What You're Interested In")

    email_param = unquote(email_param).strip().lower()
    segment_param = unquote(segment_param).strip() if segment_param else CONFIG["segments"][0]

    selected = st.radio("Please select your preferred segment below:", CONFIG["segments"],
                        index=CONFIG["segments"].index(segment_param) if segment_param in CONFIG["segments"] else 0)

    if st.button("✅ Confirm Selection"):
        try:
            segment_selector.handle_segment_selection(email_param, selected)
            st.success(f"🎉 You're now subscribed to **{selected}** updates. Watch your inbox!")
        except Exception as e:
            st.error(f"❌ Something went wrong: {e}")
    st.stop()

# ----------------- IF NO QUERY PARAMS ----------------- #
st.set_page_config(page_title="Invalid Access", page_icon="🚫")
st.title("🚫 Invalid Access")
st.write("This page is intended for users who received a link via email.")
