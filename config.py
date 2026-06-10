import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = "checkers-secret-2026"
    TEMPLATES_AUTO_RELOAD = True
    CORS_ALLOWED_ORIGINS = "*"
    DEFAULT_PORT = 5001
    MOVE_TIME_LIMIT_SECONDS = 30

    SMTP_ENABLED = os.environ.get("SMTP_ENABLED", "false").lower() == "true"
    SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
    SMTP_USER = os.environ.get("SMTP_USER", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", SMTP_USER)