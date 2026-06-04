"""In-memory game session storage."""

import uuid
from game_logic import initial_board, all_jumps_for_side, all_simple_moves_for_side, apply_move, check_winner

# waiting_player: sid of player waiting for opponent
waiting_player = None

# games: { game_id: { board, turn, players: {sid: side}, chat } }
games = {}

# sid_to_game: { sid: game_id }
sid_to_game = {}


def find_or_create_game(sid):
    global waiting_player
    if waiting_player and waiting_player != sid:
        opponent_sid = waiting_player
        waiting_player = None
        game_id = str(uuid.uuid4())
        games[game_id] = {
            "board": initial_board(),
            "turn": "white",
            "players": {opponent_sid: "white", sid: "black"},
            "chat": [],
            "winner": None,
        }
        sid_to_game[opponent_sid] = game_id
        sid_to_game[sid] = game_id
        return game_id, "created"
    else:
        waiting_player = sid
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


def make_move(game, move):
    game["board"] = apply_move(game["board"], move)
    winner = check_winner(game["board"])
    if winner:
        game["winner"] = winner
    else:
        game["turn"] = "black" if game["turn"] == "white" else "white"
    return winner


def remove_player(sid):
    global waiting_player
    if waiting_player == sid:
        waiting_player = None
    game_id, game = get_game(sid)
    if game_id:
        del sid_to_game[sid]
        # mark opponent as disconnected if still in game
        for other_sid in list(game["players"].keys()):
            if other_sid != sid and other_sid in sid_to_game:
                return game_id, other_sid
    return None, None
