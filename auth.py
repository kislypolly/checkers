"""In-memory user accounts."""

import re

from werkzeug.security import check_password_hash, generate_password_hash

users = {}
sid_to_username = {}

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def register(username, password, email):
    username = username.strip()
    email = email.strip().lower()
    if not USERNAME_RE.match(username):
        return False, "Имя: 3–20 символов, латиница, цифры, _"
    if not EMAIL_RE.match(email):
        return False, "Укажите корректный email"
    if len(password) < 4:
        return False, "Пароль: минимум 4 символа"
    if username in users:
        return False, "Пользователь уже существует"
    if any(u["email"] == email for u in users.values()):
        return False, "Email уже используется"
    users[username] = {
        "password_hash": generate_password_hash(password),
        "email": email,
        "trophies": 0,
    }
    return True, None


def authenticate(username, password):
    user = users.get(username.strip())
    if not user or not check_password_hash(user["password_hash"], password):
        return None
    return user


def get_user(username):
    if not username:
        return None
    user = users.get(username)
    if not user:
        return None
    return {
        "username": username,
        "email": user["email"],
        "trophies": user["trophies"],
    }


def get_email(username):
    user = users.get(username)
    return user["email"] if user else None


def add_trophy(username):
    user = users.get(username)
    if not user:
        return 0
    user["trophies"] += 1
    return user["trophies"]


def bind_sid(sid, username):
    sid_to_username[sid] = username


def unbind_sid(sid):
    sid_to_username.pop(sid, None)


def get_username_for_sid(sid):
    return sid_to_username.get(sid)
