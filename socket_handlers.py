"""WebSocket event handlers."""

import time

from flask import request, session
from flask_socketio import emit, join_room, leave_room

import auth
import game_state as gs
from game_logic import board_changes_from_move
from mailer import send_opponent_joined_email


def register_handlers(socketio):

    def timer_payload(game):
        return {
            "last_move_timestamp": game["last_move_timestamp"],
            "move_time_limit": game["move_time_limit"],
            "server_time": time.time(),
        }

    def emit_ready_status(game_id, game):
        for player_sid in game["players"]:
            socketio.emit("ready_update", {
                "players": [
                    {
                        "name": game["usernames"][sid],
                        "ready": game["ready"][sid],
                        "is_you": sid == player_sid,
                    }
                    for sid in game["players"]
                ],
            }, to=player_sid)

    def emit_valid_moves(game_id, game):
        valid_moves, must_jump = gs.get_valid_moves(game)
        for player_sid, side in game["players"].items():
            if side == game["turn"]:
                socketio.emit("valid_moves", {
                    "moves": valid_moves,
                    "must_jump": must_jump,
                }, to=player_sid)
            else:
                socketio.emit("valid_moves", {
                    "moves": [],
                    "must_jump": False,
                }, to=player_sid)

    def award_winner_trophy(game, winner_side):
        if game.get("trophy_awarded"):
            return
        game["trophy_awarded"] = True
        for player_sid, side in game["players"].items():
            if side != winner_side:
                continue
            account = game.get("accounts", {}).get(player_sid)
            if not account:
                continue
            trophies = auth.add_trophy(account)
            socketio.emit("trophy_update", {"trophies": trophies}, to=player_sid)

    def start_game_if_ready(socketio, game_id, game):
        if game.get("started") or not gs.all_players_ready(game):
            return
        gs.start_game(game)
        for player_sid, side in game["players"].items():
            opponent_sid = next(s for s in game["players"] if s != player_sid)
            socketio.emit("game_start", {
                "side": side,
                "username": game["usernames"][player_sid],
                "opponent": game["usernames"][opponent_sid],
                "board": game["board"],
                "turn": game["turn"],
                **timer_payload(game),
            }, to=player_sid)
        emit_valid_moves(game_id, game)
        socketio.start_background_task(watch_game_timer, game_id)

    def notify_waiting_player(game, waiting_sid):
        account = game.get("accounts", {}).get(waiting_sid)
        if not account:
            return
        email = auth.get_email(account)
        if not email:
            return
        opponent_sid = next(s for s in game["players"] if s != waiting_sid)
        recipient = game["usernames"][waiting_sid]
        opponent = game["usernames"][opponent_sid]
        socketio.start_background_task(
            send_opponent_joined_email, email, recipient, opponent
        )

    def emit_timeout(socketio, game_id, game):
        winner, loser = gs.forfeit_on_timeout(game)
        award_winner_trophy(game, winner)
        payload = {
            "turn": game["turn"],
            "winner": winner,
            "reason": "timeout",
            "time_expired_player": loser,
            **timer_payload(game),
        }
        for player_sid, side in game["players"].items():
            if side == winner:
                account = game.get("accounts", {}).get(player_sid)
                user = auth.get_user(account)
                if user:
                    payload["winner_trophies"] = user["trophies"]
                break
        socketio.emit("board_update", payload, room=game_id)

    def watch_game_timer(game_id):
        while True:
            socketio.sleep(1)
            game = gs.games.get(game_id)
            if not game or game.get("winner") or not game.get("started"):
                return
            if gs.is_time_expired(game):
                emit_timeout(socketio, game_id, game)
                return

    def handle_timeout_if_needed(game_id, game):
        if game.get("winner") or not game.get("started") or not gs.is_time_expired(game):
            return False
        emit_timeout(socketio, game_id, game)
        return True

    @socketio.on("connect")
    def on_connect():
        username = session.get("username")
        if username and auth.get_user(username):
            auth.bind_sid(request.sid, username)

    @socketio.on("join_queue")
    def on_join_queue(data):
        sid = request.sid
        account = session.get("username")
        if account and not auth.get_user(account):
            account = None
        display = account or f"Гость {sid[:4]}"
        result = gs.find_or_create_game(sid, display, account)
        if result[1] == "waiting":
            emit("waiting", {})
            return

        game_id, _, waiting_sid = result
        game = gs.games[game_id]
        for player_sid in game["players"]:
            join_room(game_id, sid=player_sid)
            opponent_sid = next(s for s in game["players"] if s != player_sid)
            socketio.emit("match_found", {
                "opponent": game["usernames"][opponent_sid],
                "username": game["usernames"][player_sid],
            }, to=player_sid)
        notify_waiting_player(game, waiting_sid)

    @socketio.on("player_ready")
    def on_player_ready():
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or game.get("started") or game.get("winner"):
            return
        if not gs.set_player_ready(game, sid):
            return
        emit_ready_status(game_id, game)
        start_game_if_ready(socketio, game_id, game)

    @socketio.on("make_move")
    def on_make_move(data):
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or not game.get("started") or game.get("winner"):
            return
        if handle_timeout_if_needed(game_id, game):
            return

        side = gs.get_side(game, sid)
        if side != game["turn"]:
            emit("error", {"msg": "Not your turn"})
            return

        move = data.get("move")
        if not move:
            return

        valid_moves, _ = gs.get_valid_moves(game)
        valid = any(
            vm["from"] == move.get("from") and vm["path"] == move.get("path")
            for vm in valid_moves
        )
        if not valid:
            emit("invalid_move", {})
            return

        winner = gs.make_move(game, move)
        payload = {
            "board_changes": board_changes_from_move(move, game["board"]),
            "turn": game["turn"],
            "last_move": move,
            "winner": winner,
            **timer_payload(game),
        }
        if winner:
            award_winner_trophy(game, winner)
            for player_sid, side in game["players"].items():
                if side == winner:
                    account = game.get("accounts", {}).get(player_sid)
                    user = auth.get_user(account)
                    if user:
                        payload["winner_trophies"] = user["trophies"]
                    break
        socketio.emit("board_update", payload, room=game_id)

        if not winner:
            emit_valid_moves(game_id, game)

    @socketio.on("time_expired")
    def on_time_expired(data):
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or not game.get("started") or game.get("winner"):
            return
        if gs.get_side(game, sid) != game["turn"]:
            return
        handle_timeout_if_needed(game_id, game)

    @socketio.on("chat_message")
    def on_chat(data):
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or not game.get("started"):
            return
        side = gs.get_side(game, sid)
        msg = str(data.get("text", ""))[:300]
        game["chat"].append({"side": side, "text": msg})
        socketio.emit("chat_message", {"side": side, "text": msg}, room=game_id)

    @socketio.on("disconnect")
    def on_disconnect():
        sid = request.sid
        auth.unbind_sid(sid)
        game_id, opponent_sid = gs.remove_player(sid)
        if game_id and opponent_sid:
            leave_room(game_id, sid=opponent_sid)
            socketio.emit("waiting", {}, to=opponent_sid)
