import smtplib
from email.message import EmailMessage

def send_email(name, recipient_email, segment):
    sender_email = "dcgcapital3@gmail.com"
    app_password = "fykn tdfm qafy rqks"  # Your App Password
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
        msg['From'] = sender_email
        msg['To'] = recipient_email

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, app_password)
            smtp.send_message(msg)

        print("✅ Email sent successfully.")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- MANUAL TESTING --- #
if __name__ == "__main__":
    send_email("Alfonso", "Alfonsovhamana@gmail.com", "Business Financing")
