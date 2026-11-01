"""Servicio de envío de correos electrónicos"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.config import settings

logger = logging.getLogger(__name__)


class EmailService:

    @staticmethod
    def send_otp(to_email: str, code: str) -> bool:
        if not settings.SMTP_HOST:
            logger.warning("SMTP no configurado. Simulando envío de OTP %s a %s", code, to_email)
            return True

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "Código de verificación MFA - SATISUP"
            msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
            msg["To"] = to_email

            text = f"Tu código de verificación es: {code}\n\nVálido por 3 minutos."
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 400px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; padding: 24px;">
                  <h2 style="color: #1e3a5f; margin-top: 0;">SATISUP</h2>
                  <p style="color: #555;">Tu código de verificación es:</p>
                  <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px; text-align: center; color: #1e3a5f; margin: 20px 0;">
                    {code}
                  </div>
                  <p style="color: #888; font-size: 12px;">Válido por 3 minutos. No compartas este código.</p>
                </div>
              </body>
            </html>
            """

            msg.attach(MIMEText(text, "plain"))
            msg.attach(MIMEText(html, "html"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(msg["From"], to_email, msg.as_string())

            logger.info("OTP enviado a %s", to_email)
            return True
        except Exception as e:
            logger.error("Error enviando OTP a %s: %s", to_email, e)
            return False
