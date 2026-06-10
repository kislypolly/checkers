const socket = io();

// ── State ─────────────────────────────────────────
let mySide = null;
let myUsername = null;
const trophiesEl = document.getElementById("my-trophies");
const isLoggedIn = trophiesEl !== null;
let myTrophies = isLoggedIn ? parseInt(trophiesEl.textContent || "0", 10) : 0;
let board = null;
let turn = null;
let validMoves = [];
let mustJump = false;
let selectedCell = null;
let landingMoves = [];
let moveTimeLimit = null;
let lastMoveTimestamp = null;
let serverTimeOffset = 0;
let timerInterval = null;

// ── DOM refs ──────────────────────────────────────
const boardEl      = document.getElementById("board");
const statusText   = document.getElementById("status-text");
const statusBox    = document.getElementById("status-box");
const moveTimerEl  = document.getElementById("move-timer");
const chatMessages = document.getElementById("chat-messages");
const chatForm     = document.getElementById("chat-form");
const chatInput    = document.getElementById("chat-input");
const overlay      = document.getElementById("overlay");
const overlayText  = document.getElementById("overlay-text");
const overlayIcon  = document.getElementById("overlay-icon");
const dotOpponent  = document.getElementById("dot-opponent");

const EMPTY = 0, WHITE = 1, BLACK = 2, WHITE_KING = 3, BLACK_KING = 4;

// ── Timer ─────────────────────────────────────────
function syncTimer(data) {
    if (data.move_time_limit == null || data.last_move_timestamp == null) return;
    moveTimeLimit = data.move_time_limit;
    lastMoveTimestamp = data.last_move_timestamp;
    if (data.server_time != null) {
        serverTimeOffset = data.server_time - Date.now() / 1000;
    }
    startTimerLoop();
}

function serverNow() {
    return Date.now() / 1000 + serverTimeOffset;
}

function remainingSeconds() {
    if (moveTimeLimit == null || lastMoveTimestamp == null) return null;
    return Math.max(0, Math.ceil(moveTimeLimit - (serverNow() - lastMoveTimestamp)));
}

function startTimerLoop() {
    if (timerInterval) clearInterval(timerInterval);
    updateTimerDisplay();
    timerInterval = setInterval(() => {
        const remaining = remainingSeconds();
        updateTimerDisplay();
        if (remaining === 0 && turn === mySide) {
            socket.emit("time_expired", {});
        }
    }, 250);
}

function updateTimerDisplay() {
    if (!moveTimerEl) return;
    const remaining = remainingSeconds();
    if (remaining == null) {
        moveTimerEl.textContent = "";
        return;
    }
    moveTimerEl.textContent = `Время на ход: ${remaining} с`;
    moveTimerEl.classList.toggle("warning", remaining <= 10);
}

function stopTimerLoop() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
    if (moveTimerEl) {
        moveTimerEl.textContent = "";
        moveTimerEl.classList.remove("warning");
    }
}

// ── Board patches ─────────────────────────────────
function applyBoardChanges(changes) {
    if (!board || !changes) return;
    for (const change of changes) {
        board[change.row][change.col] = change.piece;
    }
}

// ── Socket events ─────────────────────────────────
socket.on("connect", () => {
    socket.emit("join_queue", {});
});

socket.on("waiting", () => {
    setStatus("Ищем противника…", false);
    stopTimerLoop();
});

socket.on("game_start", (data) => {
    mySide = data.side;
    myUsername = data.username;
    board  = data.board;
    turn   = data.turn;
    dotOpponent.classList.add("active");
    document.getElementById("label-opponent").textContent = data.opponent || "Противник";
    document.getElementById("label-self").textContent = data.username || "Вы";
    setStatus(turn === mySide ? "Ваш ход" : "Ход противника", turn === mySide);
    syncTimer(data);
    updateScore();
    renderBoard();
});

socket.on("valid_moves", (data) => {
    validMoves = data.moves;
    mustJump   = data.must_jump;
    renderBoard();
});

socket.on("board_update", (data) => {
    if (data.board) {
        board = data.board;
    } else if (data.board_changes) {
        applyBoardChanges(data.board_changes);
    }
    turn = data.turn;
    selectedCell = null;
    landingMoves = [];
    syncTimer(data);
    updateScore();

    if (data.winner) {
        if (data.winner === mySide && data.winner_trophies != null) {
            myTrophies = data.winner_trophies;
            const el = document.getElementById("my-trophies");
            if (el) el.textContent = myTrophies;
        }
        stopTimerLoop();
        renderBoard();
        showOverlay(data.winner, data.reason, data.time_expired_player);
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

socket.on("trophy_update", (data) => {
    myTrophies = data.trophies;
    const el = document.getElementById("my-trophies");
    if (el) el.textContent = myTrophies;
});

socket.on("opponent_disconnected", () => {
    stopTimerLoop();
    setStatus("Противник отключился", false);
    dotOpponent.classList.remove("active");
});

// ── Board rendering ───────────────────────────────
function renderBoard() {
    boardEl.innerHTML = "";

    const rows = mySide === "black"
        ? [7,6,5,4,3,2,1,0]
        : [0,1,2,3,4,5,6,7];
    const cols = mySide === "black"
        ? [7,6,5,4,3,2,1,0]
        : [0,1,2,3,4,5,6,7];

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
    if (!board || turn !== mySide) return;

    const piece = board[r][c];
    const isMyPiece = mySide === "white"
        ? (piece === WHITE || piece === WHITE_KING)
        : (piece === BLACK || piece === BLACK_KING);

    if (selectedCell && landingMoves.length) {
        const move = landingMoves.find(m => {
            const last = m.path[m.path.length - 1];
            return last[0] === r && last[1] === c;
        });
        if (move) {
            socket.emit("make_move", { move });
            selectedCell = null;
            landingMoves = [];
            return;
        }
    }

    if (isMyPiece) {
        const movesFrom = validMoves.filter(m => m.from[0] === r && m.from[1] === c);
        if (movesFrom.length) {
            selectedCell = [r, c];
            landingMoves = movesFrom;
            renderBoard();
            return;
        }
    }

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
function showOverlay(winner, reason, timeExpiredPlayer) {
    const won = winner === mySide;
    overlayIcon.textContent = won ? "🏆" : "💀";
    let text;
    if (reason === "timeout") {
        text = timeExpiredPlayer === mySide
            ? "Время вышло — вы проиграли"
            : "Противник не успел сходить — вы победили";
    } else {
        text = won ? "Вы победили!" : "Вы проиграли";
    }
    if (won && isLoggedIn) {
        text += `\nКубков: ${myTrophies}`;
    }
    overlayText.textContent = text;
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
    const capturedWhite = 12 - whites;
    const capturedBlack = 12 - blacks;

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
