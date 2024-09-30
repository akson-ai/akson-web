import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum

from pydantic import Field

from function_calling import Function


class SendEmail(Function):
    """Sends an email."""

    to: str = Field(description="The email address to send the email to.")
    subject: str = Field(description="The subject of the email.")
    body: str = Field(description="The body of the email.")

    class MimeSubtype(str, Enum):
        TEXT = "text"
        HTML = "html"

    mime_subtype: MimeSubtype = Field(default=MimeSubtype.HTML, description="The MIME subtype of the email.")

    def run(self):
        msg = MIMEMultipart()
        msg["From"] = os.environ["ZOHO_SMTP_EMAIL"]
        msg["To"] = self.to
        msg["Subject"] = self.subject
        msg.attach(MIMEText(self.body, self.mime_subtype.value))

        with smtplib.SMTP_SSL("smtp.zoho.com", 465) as server:
            server.login(os.environ["ZOHO_SMTP_EMAIL"], os.environ["ZOHO_SMTP_PASSWORD"])
            server.sendmail(msg["From"], msg["To"], msg.as_string())
            server.quit()
