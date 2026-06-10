import os

from dotenv import load_dotenv

load_dotenv()


def _env(key, default=""):
    val = os.environ.get(key, default)
    if val is None:
        return default
    return str(val).strip().strip('"').strip("'")


def _env_bool(key):
    return _env(key, "false").lower() in ("true", "1", "yes", "on")


class Config:
    SECRET_KEY = _env("SECRET_KEY", "checkers-secret-2026")
    TEMPLATES_AUTO_RELOAD = True
    CORS_ALLOWED_ORIGINS = "*"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = _env_bool("SESSION_COOKIE_SECURE") or bool(_env("RAILWAY_ENVIRONMENT"))
    DEFAULT_PORT = 5001
    MOVE_TIME_LIMIT_SECONDS = 30

    SMTP_USER = _env("SMTP_USER")
    SMTP_PASSWORD = _env("SMTP_PASSWORD")
    SMTP_HOST = _env("SMTP_HOST", "smtp.gmail.com")
    SMTP_PORT = int(_env("SMTP_PORT", "587") or "587")
    MAIL_FROM = _env("MAIL_FROM") or SMTP_USER
    # true явно, или авто-включение если заданы логин и пароль
    SMTP_ENABLED = _env_bool("SMTP_ENABLED") or bool(SMTP_USER and SMTP_PASSWORD)
