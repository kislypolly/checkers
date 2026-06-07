"""Russian checkers game logic."""

EMPTY = 0
WHITE = 1
BLACK = 2
WHITE_KING = 3
BLACK_KING = 4


def initial_board():
    board = [[EMPTY] * 8 for _ in range(8)]
    for row in range(3):
        for col in range(8):
            if (row + col) % 2 == 1:
                board[row][col] = BLACK
    for row in range(5, 8):
        for col in range(8):
            if (row + col) % 2 == 1:
                board[row][col] = WHITE
    return board


def is_white(piece):
    return piece in (WHITE, WHITE_KING)


def is_black(piece):
    return piece in (BLACK, BLACK_KING)


def is_king(piece):
    return piece in (WHITE_KING, BLACK_KING)


def same_side(p1, p2):
    return (is_white(p1) and is_white(p2)) or (is_black(p1) and is_black(p2))


def opponent(piece):
    if is_white(piece):
        return BLACK
    return WHITE


def promote(piece, row):
    if piece == WHITE and row == 0:
        return WHITE_KING
    if piece == BLACK and row == 7:
        return BLACK_KING
    return piece


def get_jumps(board, row, col):
    """Return list of jump sequences from (row, col)."""
    piece = board[row][col]
    results = []

    def dfs(r, c, captured, path, current_board):
        found = False
        if is_king(piece):
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                # King slides along diagonal looking for enemy
                dist = 1
                while True:
                    er, ec = r + dr * dist, c + dc * dist
                    if not (0 <= er < 8 and 0 <= ec < 8):
                        break
                    target = current_board[er][ec]
                    if target == EMPTY:
                        dist += 1
                        continue
                    if same_side(piece, target) or (er, ec) in captured:
                        break
                    # Found enemy — can land anywhere beyond
                    land = dist + 1
                    while True:
                        lr, lc = r + dr * land, c + dc * land
                        if not (0 <= lr < 8 and 0 <= lc < 8):
                            break
                        if current_board[lr][lc] != EMPTY:
                            break
                        new_board = [row_[:] for row_ in current_board]
                        new_board[lr][lc] = new_board[r][c]
                        new_board[r][c] = EMPTY
                        new_captured = captured | {(er, ec)}
                        new_path = path + [[lr, lc]]
                        found = True
                        dfs(lr, lc, new_captured, new_path, new_board)
                        land += 1
                    break
        else:
            dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in dirs:
                er, ec = r + dr, c + dc
                lr, lc = r + dr * 2, c + dc * 2
                if not (0 <= er < 8 and 0 <= ec < 8 and 0 <= lr < 8 and 0 <= lc < 8):
                    continue
                target = current_board[er][ec]
                if target == EMPTY or same_side(piece, target) or (er, ec) in captured:
                    continue
                if current_board[lr][lc] != EMPTY:
                    continue
                new_board = [row_[:] for row_ in current_board]
                new_board[lr][lc] = new_board[r][c]
                new_board[r][c] = EMPTY
                new_captured = captured | {(er, ec)}
                new_path = path + [[lr, lc]]
                found = True
                dfs(lr, lc, new_captured, new_path, new_board)

        if not found and len(path) > 1:
            results.append({"path": path, "captured": [[r, c] for r, c in captured]})

    dfs(row, col, set(), [[row, col]], board)
    return results


def get_simple_moves(board, row, col):
    piece = board[row][col]
    moves = []
    if is_king(piece):
        for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            r, c = row + dr, col + dc
            while 0 <= r < 8 and 0 <= c < 8:
                if board[r][c] != EMPTY:
                    break
                moves.append((r, c))
                r += dr
                c += dc
    else:
        forward = -1 if is_white(piece) else 1
        for dc in (-1, 1):
            r, c = row + forward, col + dc
            if 0 <= r < 8 and 0 <= c < 8 and board[r][c] == EMPTY:
                moves.append((r, c))
    return moves


def all_jumps_for_side(board, side):
    """Return all possible jump moves for a side."""
    moves = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if (side == "white" and is_white(p)) or (side == "black" and is_black(p)):
                for jump in get_jumps(board, r, c):
                    moves.append({"from": [r, c], **jump})
    return moves


def all_simple_moves_for_side(board, side):
    moves = []
    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if (side == "white" and is_white(p)) or (side == "black" and is_black(p)):
                for (tr, tc) in get_simple_moves(board, r, c):
                    moves.append({"from": [r, c], "path": [[r, c], [tr, tc]], "captured": []})
    return moves


def apply_move(board, move):
    """Apply a move dict {from, path, captured} to board. Returns new board."""
    new_board = [row[:] for row in board]
    fr, fc = move["from"]
    piece = new_board[fr][fc]
    tr, tc = move["path"][-1]

    new_board[fr][fc] = EMPTY
    new_board[tr][tc] = piece

    for cr, cc in move["captured"]:
        new_board[cr][cc] = EMPTY

    new_board[tr][tc] = promote(new_board[tr][tc], tr)
    return new_board


def board_changes_from_move(move, board_after):
    """Return only changed cells after a move for compact WebSocket updates."""
    changes = []
    fr, fc = move["from"]
    tr, tc = move["path"][-1]
    seen = set()

    for row, col in [(fr, fc), (tr, tc), *move["captured"]]:
        key = (row, col)
        if key in seen:
            continue
        seen.add(key)
        changes.append({"row": row, "col": col, "piece": board_after[row][col]})

    return changes


def check_winner(board):
    whites = sum(1 for r in range(8) for c in range(8) if is_white(board[r][c]))
    blacks = sum(1 for r in range(8) for c in range(8) if is_black(board[r][c]))
    if whites == 0:
        return "black"
    if blacks == 0:
        return "white"
    if not all_jumps_for_side(board, "white") and not all_simple_moves_for_side(board, "white"):
        return "black"
    if not all_jumps_for_side(board, "black") and not all_simple_moves_for_side(board, "black"):
        return "white"
    return None
