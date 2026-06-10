"""Email notifications."""

import smtplib
import traceback
from email.mime.text import MIMEText

from config import Config


def send_opponent_joined_email(to_email, recipient_name, opponent_name):
    subject = "Шашки — противник найден"
    body = (
        f"Здравствуйте, {recipient_name}!\n\n"
        f"Игрок {opponent_name} присоединился к вашей партии.\n"
        f"Зайдите в игру и подтвердите готовность, чтобы начать.\n\n"
        f"— Шашки онлайн"
    )
    return _send(to_email, subject, body)


def _send(to_email, subject, body):
    if not to_email:
        return False

    if not Config.SMTP_ENABLED:
        print(f"[EMAIL] To: {to_email}\nSubject: {subject}\n{body}\n")
        return True

    return _send_smtp(to_email, subject, body)


def _send_smtp(to_email, subject, body):
    smtp_user = (Config.SMTP_USER or "").strip()
    smtp_password = (Config.SMTP_PASSWORD or "").replace(" ", "")

    if not smtp_user or not smtp_password:
        print("[EMAIL ERROR] SMTP_USER или SMTP_PASSWORD не заданы")
        return False

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = (Config.MAIL_FROM or smtp_user).strip()
    msg["To"] = to_email

    try:
        if Config.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(msg["From"], [to_email], msg.as_string())
        else:
            with smtplib.SMTP(Config.SMTP_HOST, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(msg["From"], [to_email], msg.as_string())
        print(f"[EMAIL] Sent to {to_email}")
        return True
    except smtplib.SMTPAuthenticationError:
        print(
            "[EMAIL ERROR] Gmail отклонил логин. "
            "Нужен пароль приложения (не обычный пароль): "
            "https://myaccount.google.com/apppasswords"
        )
        return False
    except Exception:
        print(f"[EMAIL ERROR] SMTP failed for {to_email}")
        traceback.print_exc()
        return False
