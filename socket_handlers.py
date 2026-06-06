"""WebSocket event handlers."""

import time

from flask import request
from flask_socketio import emit, join_room

import game_state as gs
from game_logic import board_changes_from_move


def register_handlers(socketio):

    def timer_payload(game):
        return {
            "last_move_timestamp": game["last_move_timestamp"],
            "move_time_limit": game["move_time_limit"],
            "server_time": time.time(),
        }

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

    def emit_timeout(socketio, game_id, game):
        winner, loser = gs.forfeit_on_timeout(game)
        socketio.emit("board_update", {
            "turn": game["turn"],
            "winner": winner,
            "reason": "timeout",
            "time_expired_player": loser,
            **timer_payload(game),
        }, room=game_id)

    def watch_game_timer(game_id):
        while True:
            socketio.sleep(1)
            game = gs.games.get(game_id)
            if not game or game.get("winner"):
                return
            if gs.is_time_expired(game):
                emit_timeout(socketio, game_id, game)
                return

    def handle_timeout_if_needed(game_id, game):
        if game.get("winner") or not gs.is_time_expired(game):
            return False
        emit_timeout(socketio, game_id, game)
        return True

    @socketio.on("connect")
    def on_connect():
        pass

    @socketio.on("join_queue")
    def on_join_queue(data):
        sid = request.sid
        game_id, status = gs.find_or_create_game(sid)
        if status == "waiting":
            emit("waiting", {})
            return

        game = gs.games[game_id]
        for player_sid, side in game["players"].items():
            join_room(game_id, sid=player_sid)
            socketio.emit("game_start", {
                "side": side,
                "board": game["board"],
                "turn": game["turn"],
                **timer_payload(game),
            }, to=player_sid)
        emit_valid_moves(game_id, game)
        socketio.start_background_task(watch_game_timer, game_id)

    @socketio.on("make_move")
    def on_make_move(data):
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or game.get("winner"):
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
        socketio.emit("board_update", payload, room=game_id)

        if not winner:
            emit_valid_moves(game_id, game)

    @socketio.on("time_expired")
    def on_time_expired(data):
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or game.get("winner"):
            return
        if gs.get_side(game, sid) != game["turn"]:
            return
        handle_timeout_if_needed(game_id, game)

    @socketio.on("chat_message")
    def on_chat(data):
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game:
            return
        side = gs.get_side(game, sid)
        msg = str(data.get("text", ""))[:300]
        game["chat"].append({"side": side, "text": msg})
        socketio.emit("chat_message", {"side": side, "text": msg}, room=game_id)

    @socketio.on("disconnect")
    def on_disconnect():
        sid = request.sid
        game_id, opponent_sid = gs.remove_player(sid)
        if game_id and opponent_sid:
            socketio.emit("opponent_disconnected", {}, to=opponent_sid)
