import logging
import smtplib
import requests
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.config import config

class NotificationService:
    def __init__(self):
        self.log = logging.getLogger("notifications")

    def send_message(self, message: str):
        """Send a simple text message to all configured channels."""
        self._send_discord(message)
        self._send_telegram(message)
        # Email is typically used for richer content, but we can send text too if needed
        # For this refactor, I'll keep email focused on html content or errors as per original

    def send_email(self, subject: str, html_body: str):
        """Send an HTML email if configured."""
        if not config.NOTIFY_EMAIL or not config.EMAIL or not config.EMAIL_PASSWORD:
            return

        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = config.EMAIL
        message["To"] = config.EMAIL
        message.attach(MIMEText(html_body, "html"))

        try:
            with smtplib.SMTP("smtp.gmail.com", 587) as server:
                server.starttls()
                server.login(config.EMAIL, config.EMAIL_PASSWORD)
                server.sendmail(config.EMAIL, config.EMAIL, message.as_string())
            self.log.info("Email sent successfully.")
        except Exception as e:
            self.log.error(f"Failed to send email: {e}")

    def _send_discord(self, message: str):
        if not config.DISCORD_WEBHOOK:
            return
        
        try:
            payload = {"content": message}
            response = requests.post(config.DISCORD_WEBHOOK, json=payload)
            response.raise_for_status()
        except Exception as e:
            self.log.error(f"Failed to send Discord message: {e}")

    def _send_telegram(self, message: str):
        if not config.TELEGRAM_TOKEN or not config.TELEGRAM_USER_ID:
            return

        try:
            url = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}/sendMessage"
            payload = {
                "chat_id": config.TELEGRAM_USER_ID,
                "text": message
            }
            response = requests.post(url, json=payload)
            response.raise_for_status()
        except Exception as e:
            self.log.error(f"Failed to send Telegram message: {e}")

    def notify_success(self, instance_details: str, html_body: str):
        """Notify success via all channels."""
        success_msg = "🎉 Success! OCI Instance has been created. Time to celebrate!"
        self.send_message(success_msg)
        self.send_email('OCI INSTANCE CREATED', html_body)

    def notify_failure(self, error_message: str):
        """Notify failure via all channels."""
        header = "😱 Oops! Something went wrong with the OCI Instance Creation Script:"
        full_msg = f"{header}\n{error_message}"
        self.send_message(full_msg)
        
        # Also send email for unhandled errors including details
        email_body = (
            f"The script encountered an unhandled error and exited unexpectedly.<br><br>"
            f"Please re-run the script by executing './setup_init.sh rerun'.<br><br>"
            f"Error details:<br><pre>{error_message}</pre>"
        )
        self.send_email('OCI INSTANCE CREATION SCRIPT: FAILED DUE TO AN ERROR', email_body)

notifications = NotificationService()
