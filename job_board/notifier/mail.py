import base64
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.oauth2 import service_account
from job_board import config
from job_board.logger import logger

# Set the API scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


class EmailProvider:
    def __init__(self, *args, **kwargs) -> None:
        self.service = self.create_service(*args, **kwargs)

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

    def send_email(
        self,
        *,
        sender: str,
        receivers: list[str],
        subject: str,
        body: str,
        references: list[str] | None = None,
        thread_id: str | None = None,
    ):
        """
        Docs: https://developers.google.com/gmail/api/guides/sending#python
        """
        message = MIMEMultipart()
        message["from"] = sender
        message["to"] = ", ".join(receivers)
        message["subject"] = subject
        msg = MIMEText(body, "html")
        message.attach(msg)

        if thread_id:
            message["threadId"] = f"<{thread_id}>@mail.gmail.com"

        if references:
            message["References"] = " ".join(
                f"<{r}@mail.gmail.com>" for r in references
            )
            message["In-Reply-To"] = f"<{references[-1]}@mail.gmail.com>"

        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        sent_message = (
            self.service.users()
            .messages()
            .send(userId=sender, body={"raw": raw_message})
            .execute()
        )
        logger.debug(
            (
                f"Message Id: {message['id']}, "
                f"Subject: {subject}, "
                f"References: {message.get('References')}, "
                f"Thread Id: {message.get('threadId')}, ",
                f"In-Reply-To: {message.get('In-Reply-To')}",
            )
        )
        return sent_message
