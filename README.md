# DCG Email App

This is a Python-based email collection and segmentation tool built for Doriscar Capital Group.

## 💼 Features

- Collects user info via Streamlit form
- Sends personalized welcome emails using Gmail SMTP
- Automatically tags users into segments:
  - Business Financing
  - Credit Building
  - Financial Education
  - Referral & Partnership Opportunities

## 🛠 Technologies

- Python
- Streamlit
- Gmail API
- Google Sheets (planned integration)

## 🚀 Run Locally

```bash
streamlit run form_app.py

# Setup instructions
cp config.template.yaml config.yaml
# then fill in your real values

