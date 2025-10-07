const AUTH_BASE = document.getElementById("authBase").textContent.trim();
const BOOKS_BASE = document.getElementById("booksBase").textContent.trim();

const logEl = document.getElementById("log");
const xmlViewer = document.getElementById("xmlViewer");
const authStatus = document.getElementById("authStatus");
const countdown = document.getElementById("countdown");
const localJwtEl = document.getElementById("localJwt");
const redisJwtEl = document.getElementById("redisJwt");

const btnLogin = document.getElementById("btnLogin");
const btnRegister = document.getElementById("btnRegister");
const btnLogout = document.getElementById("btnLogout");
const btnGetAll = document.getElementById("btnGetAll");
const btnGetByIsbn = document.getElementById("btnGetByIsbn");
const btnCompare = document.getElementById("btnCompare");

const emailEl = document.getElementById("email");
const passEl = document.getElementById("password");
const isbnEl = document.getElementById("isbn");

let accessToken = null;
let accessExp = null; // epoch seconds
let refreshToken = null;

function log(msg, obj) {
	const ts = new Date().toISOString();
	logEl.textContent += `[${ts}] ${msg}` + (obj ? `\n${JSON.stringify(obj, null, 2)}\n` : "\n");
	logEl.scrollTop = logEl.scrollHeight;
}

function decodeJwt(token) {
	const [, payloadB64] = token.split(".");
	const json = atob(payloadB64.replaceAll("-", "+").replaceAll("_", "/"));
	return JSON.parse(json);
}

function setAuthState(on, username) {
	if (on) {
		authStatus.textContent = `Autenticado como ${username}`;
		btnLogout.disabled = false;
		btnGetAll.disabled = false;
		btnGetByIsbn.disabled = false;
		btnCompare.disabled = true; // se habilita tras login ok
	} else {
		authStatus.textContent = "No autenticado";
		btnLogout.disabled = true;
		btnGetAll.disabled = true;
		btnGetByIsbn.disabled = true;
		btnCompare.disabled = true;
		countdown.textContent = "";
		localJwtEl.textContent = "";
		redisJwtEl.textContent = "";
	}
}

let countdownTimer = null;
function startCountdown() {
	if (!accessExp) return;
	if (countdownTimer) clearInterval(countdownTimer);
	countdownTimer = setInterval(() => {
		const now = Math.floor(Date.now() / 1000);
		const left = accessExp - now;
		countdown.textContent = `Access expira en ${left}s`;
		if (left <= 0) countdown.textContent = `Access expirado`;
	}, 1000);
}

async function apiFetch(url, opts = {}) {
	const headers = Object.assign({ Accept: "application/xml" }, opts.headers || {});
	if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
	const res = await fetch(url, { ...opts, headers });
	if (res.status === 401 && refreshToken) {
		log("401 recibido, intentando refresh...");
		const ok = await doRefresh();
		if (!ok) throw new Error("Refresh falló");
		headers["Authorization"] = `Bearer ${accessToken}`;
		return fetch(url, { ...opts, headers });
	}
	return res;
}

async function doRefresh() {
	try {
		const r = await fetch(`${AUTH_BASE}/auth/refresh`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ refresh_token: refreshToken }),
		});
		const j = await r.json();
		if (!r.ok) {
			log("refresh error", j);
			return false;
		}
		accessToken = j.access_token;
		const decoded = decodeJwt(accessToken);
		accessExp = decoded.exp;
		log("Nuevo access emitido", { exp: new Date(accessExp * 1000).toISOString() });
		startCountdown();
		return true;
	} catch (e) {
		log("refresh exception", { e: String(e) });
		return false;
	}
}

btnRegister.onclick = async () => {
	try {
		const r = await fetch(`${AUTH_BASE}/auth/register`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email: emailEl.value.trim(), username: emailEl.value.trim(), password: passEl.value }),
		});
		const j = await r.json();
		if (!r.ok) {
			log("register error", j);
			return;
		}
		accessToken = j.tokens.access_token;
		refreshToken = j.tokens.refresh_token;
		const d = decodeJwt(accessToken);
		accessExp = d.exp;
		setAuthState(true, d.username || j.user.username);
		btnCompare.disabled = false;
		log("register ok", { user: j.user, access_exp: j.tokens.access_expires_at_utc });
		startCountdown();
	} catch (e) {
		log("register exception", { e: String(e) });
	}
};

btnLogin.onclick = async () => {
	try {
		const r = await fetch(`${AUTH_BASE}/auth/login`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ email: emailEl.value.trim(), password: passEl.value }),
		});
		const j = await r.json();
		if (!r.ok) {
			log("login error", j);
			return;
		}
		accessToken = j.tokens.access_token;
		refreshToken = j.tokens.refresh_token;
		const d = decodeJwt(accessToken);
		accessExp = d.exp;
		setAuthState(true, d.username || j.user.username);
		btnCompare.disabled = false;
		localJwtEl.textContent = JSON.stringify(d, null, 2);
		log("login ok", { user: j.user, access_exp: j.tokens.access_expires_at_utc });
		startCountdown();
	} catch (e) {
		log("login exception", { e: String(e) });
	}
};

btnLogout.onclick = async () => {
	try {
		const r = await fetch(`${AUTH_BASE}/auth/logout`, {
			method: "POST",
			headers: { "Content-Type": "application/json", Authorization: `Bearer ${accessToken}` },
			body: JSON.stringify({ refresh_token: refreshToken }),
		});
		const j = await r.json();
		log("logout", j);
	} catch (e) {
		log("logout exception", { e: String(e) });
	}
	accessToken = null;
	refreshToken = null;
	accessExp = null;
	setAuthState(false);
};

btnGetAll.onclick = async () => {
	try {
		const res = await apiFetch(`${BOOKS_BASE}/api/books`);
		const txt = await res.text();
		xmlViewer.srcdoc = txt; // para ver el XML con XSL
		log("GET /api/books status " + res.status);
	} catch (e) {
		log("GET all exception", { e: String(e) });
	}
};

btnGetByIsbn.onclick = async () => {
	const isbn = isbnEl.value.trim();
	if (!isbn) return;
	try {
		const res = await apiFetch(`${BOOKS_BASE}/api/books/isbn/${encodeURIComponent(isbn)}`);
		const txt = await res.text();
		xmlViewer.srcdoc = txt;
		log("GET /api/books/isbn status " + res.status);
	} catch (e) {
		log("GET by isbn exception", { e: String(e) });
	}
};

btnCompare.onclick = async () => {
	if (!accessToken) return;
	// Local decode
	try {
		const d = decodeJwt(accessToken);
		localJwtEl.textContent = JSON.stringify(d, null, 2);
	} catch (e) {
		localJwtEl.textContent = "Error al decodificar local: " + String(e);
	}
	// Redis introspection
	try {
		const r = await fetch(`${AUTH_BASE}/auth/introspect`, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ token: accessToken }),
		});
		const j = await r.json();
		redisJwtEl.textContent = JSON.stringify(j, null, 2);
	} catch (e) {
		redisJwtEl.textContent = "Error introspect: " + String(e);
	}
};
