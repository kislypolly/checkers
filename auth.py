"""In-memory user accounts."""

import re

from werkzeug.security import check_password_hash, generate_password_hash

users = {}
sid_to_username = {}

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


def register(username, password):
    username = username.strip()
    if not USERNAME_RE.match(username):
        return False, "Имя: 3–20 символов, латиница, цифры, _"
    if len(password) < 4:
        return False, "Пароль: минимум 4 символа"
    if username in users:
        return False, "Пользователь уже существует"
    users[username] = {
        "password_hash": generate_password_hash(password),
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
    return {"username": username, "trophies": user["trophies"]}


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
