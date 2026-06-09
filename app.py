import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
socketio = SocketIO(app, cors_allowed_origins=app.config["CORS_ALLOWED_ORIGINS"], async_mode="threading")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/game")
def game():
    return render_template("game.html")


@app.route("/info")
def info():
    return render_template("info.html")


from socket_handlers import register_handlers
register_handlers(socketio)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", app.config["DEFAULT_PORT"]))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)
