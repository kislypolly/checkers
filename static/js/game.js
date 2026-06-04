const socket = io();

// ── State ─────────────────────────────────────────
let mySide = null;
let board = null;
let turn = null;
let validMoves = [];
let mustJump = false;
let selectedCell = null;   // [row, col] of selected piece
let landingMoves = [];     // valid moves from selected cell

// ── DOM refs ──────────────────────────────────────
const boardEl      = document.getElementById("board");
const statusText   = document.getElementById("status-text");
const statusBox    = document.getElementById("status-box");
const chatMessages = document.getElementById("chat-messages");
const chatForm     = document.getElementById("chat-form");
const chatInput    = document.getElementById("chat-input");
const overlay      = document.getElementById("overlay");
const overlayText  = document.getElementById("overlay-text");
const overlayIcon  = document.getElementById("overlay-icon");
const dotOpponent  = document.getElementById("dot-opponent");

// Piece constants (mirror server)
const EMPTY = 0, WHITE = 1, BLACK = 2, WHITE_KING = 3, BLACK_KING = 4;

// ── Socket events ─────────────────────────────────
socket.on("connect", () => {
    console.log("connected, sid:", socket.id);
    socket.emit("join_queue", {});
});

socket.on("waiting", () => {
    setStatus("Ищем противника…", false);
});

socket.on("game_start", (data) => {
    console.log("game_start received:", data.side, "turn:", data.turn);
    mySide = data.side;
    board  = data.board;
    turn   = data.turn;
    dotOpponent.classList.add("active");
    setStatus(turn === mySide ? "Ваш ход" : "Ход противника", turn === mySide);
    updateScore();
    renderBoard();
});

socket.on("valid_moves", (data) => {
    console.log("valid_moves received:", data.moves.length, "moves, mustJump:", data.must_jump);
    validMoves = data.moves;
    mustJump   = data.must_jump;
    renderBoard();
});

socket.on("board_update", (data) => {
    board  = data.board;
    turn   = data.turn;
    selectedCell  = null;
    landingMoves  = [];
    updateScore();
    if (data.winner) {
        renderBoard();
        showOverlay(data.winner);
        return;
    }
    setStatus(turn === mySide ? "Ваш ход" : "Ход противника", turn === mySide);
    renderBoard();
});

socket.on("invalid_move", () => {
    selectedCell = null;
    landingMoves = [];
    renderBoard();
});

socket.on("chat_message", (data) => {
    appendChat(data.side, data.text);
});

socket.on("opponent_disconnected", () => {
    setStatus("Противник отключился", false);
    dotOpponent.classList.remove("active");
});

// ── Board rendering ───────────────────────────────
function renderBoard() {
    boardEl.innerHTML = "";

    // Determine which rows to show first (flip board for black)
    const rows = mySide === "black"
        ? [7,6,5,4,3,2,1,0]
        : [0,1,2,3,4,5,6,7];
    const cols = mySide === "black"
        ? [7,6,5,4,3,2,1,0]
        : [0,1,2,3,4,5,6,7];

    // Precompute sets for quick lookup
    const canMoveSet  = new Set(validMoves.map(m => key(m.from[0], m.from[1])));
    const landSet     = new Set(landingMoves.map(m => key(m.path[m.path.length-1][0], m.path[m.path.length-1][1])));
    const captureSet  = new Set();
    if (selectedCell) {
        landingMoves.forEach(m => m.captured.forEach(c => captureSet.add(key(c[0], c[1]))));
    }

    for (const r of rows) {
        for (const c of cols) {
            const cell = document.createElement("div");
            cell.className = "cell " + ((r + c) % 2 === 0 ? "light" : "dark");
            cell.dataset.row = r;
            cell.dataset.col = c;

            const isSelected = selectedCell && selectedCell[0] === r && selectedCell[1] === c;
            const isCanMove  = canMoveSet.has(key(r, c));
            const isLand     = landSet.has(key(r, c));
            const isCapture  = captureSet.has(key(r, c));

            if (isSelected)  cell.classList.add("selected");
            if (isCanMove && !selectedCell)   cell.classList.add("can-move");
            if (isLand)      cell.classList.add("can-land");
            if (isCapture)   cell.classList.add("capture-hint");

            const piece = board[r][c];
            if (piece !== EMPTY) {
                const pieceEl = document.createElement("div");
                pieceEl.className = "piece " +
                    (piece === WHITE || piece === WHITE_KING ? "white-piece" : "black-piece") +
                    (piece === WHITE_KING || piece === BLACK_KING ? " king" : "") +
                    (isSelected ? " selected-piece" : "");
                cell.appendChild(pieceEl);
            }

            cell.addEventListener("click", () => onCellClick(r, c));
            boardEl.appendChild(cell);
        }
    }
}

function key(r, c) { return r * 8 + c; }

// ── Interaction ───────────────────────────────────
function onCellClick(r, c) {
    console.log(`click [${r},${c}] turn=${turn} mySide=${mySide} selectedCell=${JSON.stringify(selectedCell)} validMoves=${validMoves.length}`);
    if (!board || turn !== mySide) return;

    const piece = board[r][c];
    const isMyPiece = mySide === "white"
        ? (piece === WHITE || piece === WHITE_KING)
        : (piece === BLACK || piece === BLACK_KING);

    // Click on a landing cell
    if (selectedCell && landingMoves.length) {
        const move = landingMoves.find(m => {
            const last = m.path[m.path.length - 1];
            return last[0] === r && last[1] === c;
        });
        console.log(`  landing check: found=${!!move}, landingMoves=`, JSON.stringify(landingMoves));
        if (move) {
            console.log("  sending move:", JSON.stringify(move));
            socket.emit("make_move", { move });
            selectedCell = null;
            landingMoves = [];
            return;
        }
    }

    // Click on own piece that can move
    if (isMyPiece) {
        const movesFrom = validMoves.filter(m => m.from[0] === r && m.from[1] === c);
        console.log(`  isMyPiece=true, movesFrom=${movesFrom.length}`);
        if (movesFrom.length) {
            selectedCell = [r, c];
            landingMoves = movesFrom;
            renderBoard();
            return;
        }
    }

    // Deselect
    selectedCell = null;
    landingMoves = [];
    renderBoard();
}

// ── Chat ──────────────────────────────────────────
chatForm.addEventListener("submit", (e) => {
    e.preventDefault();
    const text = chatInput.value.trim();
    if (!text) return;
    socket.emit("chat_message", { text });
    chatInput.value = "";
});

function appendChat(side, text) {
    const isMine = side === mySide;
    const div = document.createElement("div");
    div.className = "chat-msg " + (isMine ? "me" : "them");
    const label = document.createElement("div");
    label.className = "msg-label";
    label.textContent = isMine ? "Вы" : "Противник";
    div.appendChild(label);
    div.appendChild(document.createTextNode(text));
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// ── Overlay ───────────────────────────────────────
function showOverlay(winner) {
    const won = winner === mySide;
    overlayIcon.textContent = won ? "🏆" : "💀";
    overlayText.textContent = won ? "Вы победили!" : "Вы проиграли";
    overlay.classList.remove("hidden");
}

// ── Status ────────────────────────────────────────
function updateScore() {
    if (!board || !mySide) return;
    let whites = 0, blacks = 0;
    for (let r = 0; r < 8; r++)
        for (let c = 0; c < 8; c++) {
            const p = board[r][c];
            if (p === WHITE || p === WHITE_KING) whites++;
            if (p === BLACK || p === BLACK_KING) blacks++;
        }
    const capturedWhite = 12 - whites; // сколько белых съедено
    const capturedBlack = 12 - blacks; // сколько чёрных съедено

    // Обновляем счётчики шашек на карточках игроков
    const numSelf = document.getElementById("num-self");
    const numOpp  = document.getElementById("num-opponent");
    if (numSelf) numSelf.textContent = mySide === "white" ? whites : blacks;
    if (numOpp)  numOpp.textContent  = mySide === "white" ? blacks : whites;

    const capturedByMe       = mySide === "white" ? capturedBlack : capturedWhite;
    const capturedByOpponent = mySide === "white" ? capturedWhite : capturedBlack;

    const elMe  = document.getElementById("captured-by-me");
    const elOpp = document.getElementById("captured-by-opponent");
    if (elMe)  elMe.textContent  = capturedByMe;
    if (elOpp) elOpp.textContent = capturedByOpponent;
}

function setStatus(text, isYourTurn) {
    statusText.textContent = text;
    statusBox.className = "status-box" + (isYourTurn ? " your-turn" : " opponent-turn");
}
