const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const authError = document.getElementById("auth-error");
const logoutBtn = document.getElementById("logout-btn");

document.querySelectorAll(".auth-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
        document.querySelectorAll(".auth-tab").forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const isLogin = tab.dataset.tab === "login";
        loginForm.classList.toggle("hidden", !isLogin);
        registerForm.classList.toggle("hidden", isLogin);
        hideError();
    });
});

function showError(msg) {
    if (!authError) return;
    authError.textContent = msg;
    authError.classList.remove("hidden");
}

function hideError() {
    if (!authError) return;
    authError.textContent = "";
    authError.classList.add("hidden");
}

async function submitAuth(url, form) {
    hideError();
    const data = Object.fromEntries(new FormData(form));
    const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
    });
    const payload = await res.json();
    if (!payload.ok) {
        showError(payload.error || "Ошибка");
        return;
    }
    const next = new URLSearchParams(window.location.search).get("next") || "/";
    window.location.href = next;
}

if (loginForm) {
    loginForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitAuth("/api/login", loginForm);
    });
}

if (registerForm) {
    registerForm.addEventListener("submit", (e) => {
        e.preventDefault();
        submitAuth("/api/register", registerForm);
    });
}

if (logoutBtn) {
    logoutBtn.addEventListener("click", async () => {
        await fetch("/api/logout", { method: "POST" });
        window.location.reload();
    });
}
