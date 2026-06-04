"""WebSocket event handlers."""

from flask_socketio import emit, join_room
import game_state as gs


def register_handlers(socketio):

    def emit_valid_moves(game_id, game):
        valid_moves, must_jump = gs.get_valid_moves(game)
        for player_sid, side in game["players"].items():
            if side == game["turn"]:
                socketio.emit("valid_moves", {
                    "moves": valid_moves,
                    "must_jump": must_jump
                }, to=player_sid)
            else:
                socketio.emit("valid_moves", {
                    "moves": [],
                    "must_jump": False
                }, to=player_sid)

    @socketio.on("connect")
    def on_connect():
        pass

    @socketio.on("join_queue")
    def on_join_queue(data):
        from flask import request
        sid = request.sid
        game_id, status = gs.find_or_create_game(sid)
        if status == "waiting":
            emit("waiting", {})
        else:
            game = gs.games[game_id]
            for player_sid, side in game["players"].items():
                join_room(game_id, sid=player_sid)
                socketio.emit("game_start", {
                    "side": side,
                    "board": game["board"],
                    "turn": game["turn"],
                }, to=player_sid)
            emit_valid_moves(game_id, game)

    @socketio.on("make_move")
    def on_make_move(data):
        from flask import request
        sid = request.sid
        game_id, game = gs.get_game(sid)
        if not game or game.get("winner"):
            return
        side = gs.get_side(game, sid)
        if side != game["turn"]:
            emit("error", {"msg": "Not your turn"})
            return

        move = data.get("move")
        if not move:
            return

        valid_moves, must_jump = gs.get_valid_moves(game)
        valid = any(
            vm["from"] == move.get("from") and vm["path"] == move.get("path")
            for vm in valid_moves
        )
        if not valid:
            emit("invalid_move", {})
            return

        winner = gs.make_move(game, move)
        socketio.emit("board_update", {
            "board": game["board"],
            "turn": game["turn"],
            "last_move": move,
            "winner": winner,
        }, room=game_id)

        if not winner:
            emit_valid_moves(game_id, game)

    @socketio.on("chat_message")
    def on_chat(data):
        from flask import request
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
        from flask import request
        sid = request.sid
        game_id, opponent_sid = gs.remove_player(sid)
        if game_id and opponent_sid:
            socketio.emit("opponent_disconnected", {}, to=opponent_sid)
