import base64
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2 import service_account
from job_notifier import config, logger

# Set the API scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailProvider:
    def __init__(self, *args, **kwargs) -> None:
        self.service = self.create_service()

    # Function to create a service instance
    def create_service(self, *args, **kwargs):
        creds = service_account.Credentials.from_service_account_file(
            config.SERVICE_ACCOUNT_KEY_FILE_PATH,
            scopes=SCOPES,
            subject=config.SERVER_EMAIL,
            *args,
            **kwargs,
        )

        # Build the Gmail API service
        service = build("gmail", "v1", credentials=creds)
        return service

    # Function to send an email
    def send_email(self, sender, to, subject, body):
        message = MIMEMultipart()
        message["to"] = to
        message["subject"] = subject
        msg = MIMEText(body)
        message.attach(msg)

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        message = (
            self.service.users()
            .messages()
            .send(userId=sender, body={"raw": raw_message})
            .execute()
        )
        logger.debug(f"Message Id: {message['id']}")
        return message
