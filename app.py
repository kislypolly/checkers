import os

from flask import Flask, jsonify, render_template, request, session
from flask_socketio import SocketIO

import auth
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(
    app,
    cors_allowed_origins=app.config["CORS_ALLOWED_ORIGINS"],
    async_mode="threading",
    manage_session=False,
)


@app.route("/")
def index():
    user = auth.get_user(session.get("username"))
    return render_template("index.html", user=user)


@app.route("/game")
def game():
    user = auth.get_user(session.get("username"))
    return render_template("game.html", user=user)


@app.route("/account")
def account():
    user = auth.get_user(session.get("username"))
    return render_template("account.html", user=user)


@app.route("/info")
def info():
    return render_template("info.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", ""))
    password = str(data.get("password", ""))
    email = str(data.get("email", ""))
    ok, error = auth.register(username, password, email)
    if not ok:
        return jsonify({"ok": False, "error": error}), 400
    session["username"] = username.strip()
    user = auth.get_user(session["username"])
    return jsonify({"ok": True, "user": user})


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", ""))
    password = str(data.get("password", ""))
    user = auth.authenticate(username, password)
    if not user:
        return jsonify({"ok": False, "error": "Неверное имя или пароль"}), 401
    session["username"] = username.strip()
    return jsonify({"ok": True, "user": auth.get_user(session["username"])})


@app.route("/api/logout", methods=["POST"])
def api_logout():
    session.pop("username", None)
    return jsonify({"ok": True})


from socket_handlers import register_handlers
register_handlers(socketio)

print(
    f"[CONFIG] SMTP enabled={Config.SMTP_ENABLED}, "
    f"host={Config.SMTP_HOST}, user={'set' if Config.SMTP_USER else 'MISSING'}"
)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", app.config["DEFAULT_PORT"]))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
