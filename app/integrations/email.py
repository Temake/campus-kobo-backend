from email.message import EmailMessage
import logging
import smtplib

from fastapi.concurrency import run_in_threadpool

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def is_configured(self) -> bool:
        return bool(settings.brevo_smtp_login and settings.brevo_smtp_key and settings.mail_from_email)

    async def send_verification_code(self, recipient_email: str, code: str, purpose: str, expires_minutes: int) -> None:
        try:
            await run_in_threadpool(
                self._send_verification_code_sync,
                recipient_email,
                code,
                purpose,
                expires_minutes,
            )
        except Exception:
            logger.exception("Failed to send verification email to %s", recipient_email)

    def _send_verification_code_sync(self, recipient_email: str, code: str, purpose: str, expires_minutes: int) -> None:
        if not self.is_configured():
            raise RuntimeError("Email delivery is not configured")

        message = EmailMessage()
        message["Subject"] = self._subject_for_purpose(purpose)
        message["From"] = f"{settings.mail_from_name} <{settings.mail_from_email}>"
        message["To"] = recipient_email
        message.set_content(self._plain_text_body(code=code, purpose=purpose, expires_minutes=expires_minutes))

        if settings.brevo_smtp_port == 465:
            with smtplib.SMTP_SSL(settings.brevo_smtp_host, settings.brevo_smtp_port, timeout=15) as smtp:
                smtp.login(settings.brevo_smtp_login, settings.brevo_smtp_key)
                smtp.send_message(message)
        else:
            with smtplib.SMTP(settings.brevo_smtp_host, settings.brevo_smtp_port, timeout=15) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(settings.brevo_smtp_login, settings.brevo_smtp_key)
                smtp.send_message(message)

    @staticmethod
    def _subject_for_purpose(purpose: str) -> str:
        if purpose == "change_email":
            return "Confirm your new CampusKobo email"
        return "Verify your CampusKobo email"

    @staticmethod
    def _plain_text_body(code: str, purpose: str, expires_minutes: int) -> str:
        intro = "Use the code below to verify your CampusKobo account."
        if purpose == "change_email":
            intro = "Use the code below to confirm your new email address on CampusKobo."
        return (
            f"{intro}\n\n"
            f"Verification code: {code}\n\n"
            f"This code expires in {expires_minutes} minutes.\n\n"
            "If you did not request this, you can ignore this email."
        )
