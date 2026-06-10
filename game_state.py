"""In-memory game session storage."""

import time
import uuid

from config import Config
from game_logic import (
    initial_board,
    all_jumps_for_side,
    all_simple_moves_for_side,
    apply_move,
    check_winner,
)

# waiting_player: { sid, display_name, account_name } or None
waiting_player = None

# games: { game_id: { board, turn, players, usernames, accounts, chat, ... } }
games = {}

# sid_to_game: { sid: game_id }
sid_to_game = {}


def find_or_create_game(sid, display_name, account_name=None):
    global waiting_player
    if waiting_player and waiting_player["sid"] != sid:
        opponent = waiting_player
        waiting_player = None
        opponent_sid = opponent["sid"]
        game_id = str(uuid.uuid4())
        games[game_id] = {
            "board": initial_board(),
            "turn": "white",
            "players": {opponent_sid: "white", sid: "black"},
            "usernames": {
                opponent_sid: opponent["display_name"],
                sid: display_name,
            },
            "accounts": {
                opponent_sid: opponent["account_name"],
                sid: account_name,
            },
            "ready": {opponent_sid: False, sid: False},
            "started": False,
            "chat": [],
            "winner": None,
            "trophy_awarded": False,
            "last_move_timestamp": time.time(),
            "move_time_limit": Config.MOVE_TIME_LIMIT_SECONDS,
        }
        sid_to_game[opponent_sid] = game_id
        sid_to_game[sid] = game_id
        return game_id, "matched", opponent_sid
    waiting_player = {
        "sid": sid,
        "display_name": display_name,
        "account_name": account_name,
    }
    return None, "waiting"


def get_game(sid):
    game_id = sid_to_game.get(sid)
    if game_id:
        return game_id, games.get(game_id)
    return None, None


def get_side(game, sid):
    return game["players"].get(sid)


def get_valid_moves(game):
    board = game["board"]
    turn = game["turn"]
    jumps = all_jumps_for_side(board, turn)
    if jumps:
        return jumps, True
    return all_simple_moves_for_side(board, turn), False


def reset_turn_timer(game):
    game["last_move_timestamp"] = time.time()


def is_time_expired(game):
    elapsed = time.time() - game["last_move_timestamp"]
    return elapsed > game["move_time_limit"]


def forfeit_on_timeout(game):
    loser = game["turn"]
    winner = "black" if loser == "white" else "white"
    game["winner"] = winner
    return winner, loser


def make_move(game, move):
    game["board"] = apply_move(game["board"], move)
    winner = check_winner(game["board"])
    if winner:
        game["winner"] = winner
    else:
        game["turn"] = "black" if game["turn"] == "white" else "white"
        reset_turn_timer(game)
    return winner


def set_player_ready(game, sid):
    if sid not in game.get("ready", {}):
        return False
    game["ready"][sid] = True
    return True


def all_players_ready(game):
    ready = game.get("ready", {})
    return bool(ready) and all(ready.values())


def start_game(game):
    game["started"] = True
    reset_turn_timer(game)


def remove_player(sid):
    global waiting_player
    if waiting_player and waiting_player["sid"] == sid:
        waiting_player = None
        return None, None

    game_id, game = get_game(sid)
    if not game_id or not game:
        return None, None

    opponent_sid = next((s for s in game["players"] if s != sid), None)
    del sid_to_game[sid]

    if opponent_sid and opponent_sid in sid_to_game:
        waiting_player = {
            "sid": opponent_sid,
            "display_name": game["usernames"][opponent_sid],
            "account_name": game.get("accounts", {}).get(opponent_sid),
        }
        del sid_to_game[opponent_sid]
        games.pop(game_id, None)
        return game_id, opponent_sid

    games.pop(game_id, None)
    return None, None
