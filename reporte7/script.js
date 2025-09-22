// ===== Mini framework de componentes + router =====
const el = (id) => document.getElementById(id);
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));
const json = (x) => JSON.stringify(x, null, 2);
const h = (tag, props = {}, children = []) => {
	const n = document.createElement(tag);
	for (const [k, v] of Object.entries(props || {})) {
		if (k.startsWith("on") && typeof v === "function") n.addEventListener(k.slice(2).toLowerCase(), v);
		else if (k === "class") n.className = v;
		else if (k === "html") n.innerHTML = v;
		else n.setAttribute(k, v);
	}
	(Array.isArray(children) ? children : [children]).filter(Boolean).forEach((c) => {
		if (c instanceof Node) n.appendChild(c);
		else n.appendChild(document.createTextNode(String(c)));
	});
	return n;
};
function mount(view) {
	const root = el("view-root");
	root.innerHTML = "";
	root.appendChild(view);
}
function log(msg, typ = "info") {
	const now = new Date().toISOString();
	const box = el("log");
	box.textContent = `${box.textContent}
${now} ${typ.toUpperCase()}: ${msg}`.trim();
	box.scrollTop = box.scrollHeight;
}

// ===== Estado global =====
const state = {
	authBase: localStorage.getItem("authBase") || "http://172.206.106.38:5001",
	booksBase: localStorage.getItem("booksBase") || "http://172.206.106.38:5000",
	access: localStorage.getItem("access") || "",
	refresh: localStorage.getItem("refresh") || "",
};
function saveState() {
	localStorage.setItem("authBase", state.authBase);
	localStorage.setItem("booksBase", state.booksBase);
	localStorage.setItem("access", state.access || "");
	localStorage.setItem("refresh", state.refresh || "");
	setAuthUI();
}
function setAuthUI() {
	const p = decodePayload(state.access);
	el("state-badge").textContent = state.access ? "Autenticado" : "Desconectado";
	el("btn-logout").style.display = state.access ? "inline-block" : "none";
}
function copy(text) {
	navigator.clipboard
		.writeText(text || "")
		.then(() => log("Copiado"))
		.catch(() => log("No se pudo copiar", "err"));
}
function b64urlDecode(str) {
	try {
		str = str.replace(/-/g, "+").replace(/_/g, "/");
		const pad = str.length % 4;
		if (pad) str += "=".repeat(4 - pad);
		return atob(str);
	} catch {
		return "";
	}
}
function decodePayload(tok) {
	if (!tok || tok.split(".").length !== 3) return null;
	try {
		return JSON.parse(b64urlDecode(tok.split(".")[1]));
	} catch {
		return null;
	}
}

// ===== Router muy simple (hash) =====
const routes = {};
function route(path, component) {
	routes[path] = component;
}
function navigate(path) {
	if (location.hash !== `#${path}`) location.hash = `#${path}`;
	else render();
}
function render() {
	const hash = location.hash.replace(/^#/, "") || "/";
	const comp = routes[hash] || routes["/404"];
	// Migas
	drawBreadcrumbs(hash);
	// Montar vista
	mount(comp());
}
function drawBreadcrumbs(hash) {
	const bc = el("breadcrumbs");
	const parts = hash.split("/").filter(Boolean);
	const crumbs = [];
	let acc = "";
	crumbs.push(h("a", { href: "#/" }, "Inicio"));
	parts.forEach((p, i) => {
		acc += "/" + p;
		crumbs.push(document.createTextNode(" / "));
		if (i < parts.length - 1) crumbs.push(h("a", { href: "#" + acc }, decodeURIComponent(p)));
		else crumbs.push(h("span", {}, decodeURIComponent(p)));
	});
	bc.innerHTML = "";
	crumbs.forEach((c) => bc.appendChild(c));
}
window.addEventListener("hashchange", render);

// ====== VISTA: Inicio (grid de apps) ======
function ViewHome() {
	const cardAuth = h("div", { class: "app-tile", onClick: () => navigate("/auth") }, [
		h("h2", {}, "Auth"),
		h("div", { class: "muted small" }, "JWT, perfil, items protegidos"),
		h("div", { class: "sep" }),
		h("div", { class: "small muted" }, `Base: ${state.authBase}`),
	]);
	const cardBooks = h("div", { class: "app-tile", onClick: () => navigate("/books") }, [
		h("h2", {}, "Libros (XML)"),
		h("div", { class: "muted small" }, "Catálogo con búsqueda/CRUD"),
		h("div", { class: "sep" }),
		h("div", { class: "small muted" }, `Base: ${state.booksBase}`),
	]);
	const grid = h("div", { class: "app-grid" }, [cardAuth, cardBooks]);

	const cfg = h("div", { class: "card" }, [
		h("h2", {}, "Configuración rápida"),
		h("div", { class: "grid" }, [
			h("div", { class: "col-6" }, [h("label", {}, "Auth Base URL"), h("input", { id: "inAuthBase", value: state.authBase })]),
			h("div", { class: "col-6" }, [h("label", {}, "Libros Base URL"), h("input", { id: "inBooksBase", value: state.booksBase })]),
			h("div", { class: "col-12 row" }, [
				h(
					"button",
					{
						class: "btn",
						onClick: () => {
							state.authBase = $("#inAuthBase").value.trim() || state.authBase;
							state.booksBase = $("#inBooksBase").value.trim() || state.booksBase;
							saveState();
							log("URLs guardadas");
							render();
						},
					},
					"Guardar"
				),
				h("span", { class: "muted small" }, "Sirve este HTML desde 8080 para respetar CORS"),
			]),
		]),
	]);

	return h("div", {}, [h("section", { class: "card" }, [h("h2", {}, "Selecciona un microservicio"), grid]), cfg]);
}

// ====== AUTH: sub-vistas en tabs ======
function ViewAuth() {
	const tabs = [
		{ key: "register", label: "Registro", view: AuthRegister },
		{ key: "login", label: "Login", view: AuthLogin },
		{ key: "tokens", label: "Tokens", view: AuthTokens },
		{ key: "profile", label: "Perfil", view: AuthProfile },
		{ key: "items", label: "Items", view: AuthItems },
	];
	const current = location.hash.split("?")[0].split("/")[2] || "register";
	const nav = h(
		"div",
		{ class: "nav-tabs" },
		tabs.map((t) => h("div", { class: `tab ${t.key === current ? "active" : ""}`, onClick: () => navigate(`/auth/${t.key}`) }, t.label))
	);
	const content = h("div", { class: "card" }, [(tabs.find((t) => t.key === current) || tabs[0]).view()]);
	return h("div", {}, [h("section", { class: "card" }, [h("h2", {}, "Auth"), nav]), content]);
}

// --- Auth componentes ---
function AuthRegister() {
	return h("div", { class: "grid" }, [
		h("div", { class: "col-6 card" }, [
			h("h2", {}, "Registro"),
			h("label", {}, "Email"),
			h("input", { id: "regEmail", type: "email", placeholder: "alice@example.com" }),
			h("label", {}, "Usuario"),
			h("input", { id: "regUser", placeholder: "alice" }),
			h("label", {}, "Contraseña"),
			h("input", { id: "regPass", type: "password", placeholder: "••••••••" }),
			h("div", { class: "row", style: "justify-content:flex-end;margin-top:10px" }, [h("button", { class: "btn accent", onClick: doRegister }, "Crear cuenta")]),
		]),
		h("div", { class: "col-6 card" }, [
			h("h2", {}, "Login rápido"),
			h("label", {}, "Email o Usuario"),
			h("input", { id: "loginWho", placeholder: "alice o alice@example.com" }),
			h("label", {}, "Contraseña"),
			h("input", { id: "loginPass", type: "password", placeholder: "••••••••" }),
			h("div", { class: "row", style: "justify-content:flex-end;margin-top:10px" }, [h("button", { class: "btn ok", onClick: doLogin }, "Entrar")]),
		]),
	]);
}
function AuthLogin() {
	return AuthRegister();
}
function AuthTokens() {
	const accessBox = h("pre", { id: "accessToken", class: "mono muted" }, state.access || "(vacío)");
	const payloadBox = h("pre", { id: "accessPayload", class: "mono muted" }, decodePayload(state.access) ? json(decodePayload(state.access)) : "(vacío)");
	const refreshBox = h("pre", { id: "refreshToken", class: "mono muted" }, state.refresh || "(vacío)");
	return h("div", {}, [
		h("div", { class: "two-col" }, [
			h("div", { class: "card" }, [
				h("h2", {}, "Access Token"),
				h("div", { class: "row", style: "justify-content:space-between;align-items:center" }, [
					h("span", { class: "small muted" }, "Token"),
					h("button", { class: "btn small", onClick: () => copy(state.access) }, "Copiar"),
				]),
				accessBox,
				h("div", { class: "small", style: "margin-top:8px" }, "Payload:"),
				payloadBox,
			]),
			h("div", { class: "card" }, [
				h("h2", {}, "Refresh Token"),
				h("div", { class: "row", style: "justify-content:space-between;align-items:center" }, [
					h("span", { class: "small muted" }, "Token"),
					h("button", { class: "btn small", onClick: () => copy(state.refresh) }, "Copiar"),
				]),
				refreshBox,
				h("div", { class: "row", style: "gap:8px;margin-top:8px" }, [
					h("button", { class: "btn warn", onClick: doRefresh }, "Refrescar Access"),
					h("span", { class: "small muted" }, "/auth/refresh"),
				]),
			]),
		]),
	]);
}
function AuthProfile() {
	const out = h("pre", { id: "profileOut", class: "mono muted" }, "(sin datos)");
	return h("div", { class: "card" }, [
		h("h2", {}, "Perfil (protegido)"),
		h("div", { class: "row", style: "margin-bottom:8px" }, [
			h(
				"button",
				{
					class: "btn",
					onClick: async () => {
						const r = await apiFetchAuth("/api/profile", { method: "GET" });
						const j = await r.json().catch(() => ({}));
						out.textContent = json(j);
						r.ok ? log("Perfil OK") : log(`Perfil ERROR ${r.status}`, "err");
					},
				},
				"Obtener perfil"
			),
		]),
		out,
	]);
}
function AuthItems() {
	const listBox = h("div", { id: "itemsList", style: "margin-top:8px" });
	const title = h("input", { id: "itemTitle", placeholder: "Mi primer item" });
	const notes = h("input", { id: "itemNotes", placeholder: "texto..." });
	async function list() {
		const r = await apiFetchAuth("/api/items", { method: "GET" });
		const j = await r.json().catch(() => ({}));
		renderItems(j.items || []);
		r.ok ? log(`Items: ${(j.items || []).length}`) : log(`Items ERROR ${r.status}`, "err");
	}
	function renderItems(arr) {
		listBox.innerHTML = "";
		if (!arr.length) {
			listBox.innerHTML = '<div class="muted small">(sin items)</div>';
			return;
		}
		arr.forEach((it) => {
			const d = h("div", { class: "pill" }, `${it.id} • ${it.title} (${it.created_at})`);
			listBox.appendChild(d);
		});
	}
	return h("div", { class: "card" }, [
		h("h2", {}, "Items (protegido)"),
		h("div", { class: "row", style: "gap:12px;align-items:flex-end" }, [
			h("div", { style: "flex:1" }, [h("label", {}, "Título"), title]),
			h("div", { style: "flex:2" }, [h("label", {}, "Notas"), notes]),
			h(
				"button",
				{
					class: "btn ok",
					onClick: async () => {
						if (!title.value.trim()) return log("Debes poner un título", "err");
						const r = await apiFetchAuth("/api/items", {
							method: "POST",
							headers: { "Content-Type": "application/json" },
							body: JSON.stringify({ title: title.value.trim(), notes: notes.value.trim() }),
						});
						const j = await r.json().catch(() => ({}));
						if (r.ok) {
							log(`Item creado id=${j.id}`);
							title.value = "";
							notes.value = "";
							list();
						} else log(`Crear item ERROR ${r.status}`, "err");
					},
				},
				"Crear"
			),
			h("button", { class: "btn", onClick: list }, "Listar"),
		]),
		listBox,
	]);
}

// ====== BOOKS: sub-vistas en tabs ======
function ViewBooks() {
	const tabs = [
		{ key: "browse", label: "Explorar / Buscar", view: BooksBrowse },
		{ key: "insert", label: "Insertar", view: BooksInsert },
		{ key: "update", label: "Actualizar", view: BooksUpdate },
		{ key: "delete", label: "Borrar", view: BooksDelete },
		{ key: "raw", label: "Respuesta XML", view: BooksRaw },
	];
	const current = location.hash.split("/")[2] || "browse";
	const nav = h(
		"div",
		{ class: "nav-tabs" },
		tabs.map((t) => h("div", { class: `tab ${t.key === current ? "active" : ""}`, onClick: () => navigate(`/books/${t.key}`) }, t.label))
	);
	const content = h("div", { class: "card" }, [(tabs.find((t) => t.key === current) || tabs[0]).view()]);
	return h("div", {}, [h("section", { class: "card" }, [h("h2", {}, "Libros (XML)"), nav]), content]);
}

// --- Books componentes ---
let lastXML = "(sin respuesta)";
function BooksBrowse() {
	const tbody = h("tbody", { id: "booksTBody" }, h("tr", {}, h("td", { colspan: "8", class: "muted small" }, "(sin datos)")));
	const tbl = h("table", {}, [
		h(
			"thead",
			{},
			h(
				"tr",
				{},
				["ISBN", "Título", "Autor(es)", "Año", "Género", "Precio", "Stock", "Formato"].map((th) => h("th", {}, th))
			)
		),
		tbody,
	]);
	function renderRows(rows) {
		tbody.innerHTML = "";
		if (!rows.length) {
			tbody.appendChild(h("tr", {}, h("td", { colspan: "8", class: "muted small" }, "(sin datos)")));
			return;
		}
		rows.forEach((r) => {
			const tr = h("tr", {});
			tr.innerHTML = `
          <td class="mono">${escapeHtml(r.isbn)}</td>
          <td>${escapeHtml(r.title)}</td>
          <td>${escapeHtml(r.author)}</td>
          <td>${escapeHtml(r.year)}</td>
          <td>${escapeHtml(r.genre)}</td>
          <td>${escapeHtml(r.price)}</td>
          <td>${escapeHtml(r.stock)}</td>
          <td>${escapeHtml(r.format)}</td>`;
			tbody.appendChild(tr);
		});
	}
	function textXML(parent, tag) {
		const n = parent.querySelector(tag);
		return n ? n.textContent : "";
	}
	function xmlToRows(doc) {
		const rows = [];
		const books = doc.querySelectorAll("catalog > book");
		books.forEach((b) => {
			rows.push({
				isbn: b.getAttribute("isbn") || "",
				title: textXML(b, "title"),
				author: textXML(b, "author"),
				year: textXML(b, "year"),
				genre: textXML(b, "genre"),
				price: textXML(b, "price"),
				stock: textXML(b, "stock"),
				format: textXML(b, "format"),
			});
		});
		return rows;
	}
	async function fetchXML(path, opts = {}) {
		const url = state.booksBase + path;
		const r = await fetch(url, opts);
		const t = await r.text();
		lastXML = t;
		if (!r.ok) {
			log(`Libros ERROR ${r.status}`, "err");
			return null;
		}
		const doc = new DOMParser().parseFromString(t, "application/xml");
		const err = doc.querySelector("parsererror");
		if (err) {
			log("XML parse error", "err");
			return null;
		}
		return doc;
	}
	async function all() {
		const doc = await fetchXML("/api/books");
		if (!doc) return;
		renderRows(xmlToRows(doc));
		log("Libros: todos");
	}
	async function byIsbn(v) {
		const doc = await fetchXML("/api/books/isbn/" + encodeURIComponent(v));
		if (!doc) return;
		renderRows(xmlToRows(doc));
		log("Libros: por ISBN");
	}
	async function byAuthor(v) {
		const doc = await fetchXML("/api/books/author/" + encodeURIComponent(v));
		if (!doc) return;
		renderRows(xmlToRows(doc));
		log("Libros: por autor");
	}
	async function byFormat(v) {
		const doc = await fetchXML("/api/books/format/" + encodeURIComponent(v));
		if (!doc) return;
		renderRows(xmlToRows(doc));
		log("Libros: por formato");
	}

	const isbn = h("input", { placeholder: "ISBN", style: "width:200px" });
	const author = h("input", { placeholder: "Autor", style: "width:220px" });
	const format = h("input", { placeholder: "Formato (Digital/Físico)", style: "width:220px" });

	return h("div", {}, [
		h("div", { class: "row", style: "gap:8px;margin-bottom:8px" }, [
			h("button", { class: "btn", onClick: all }, "Listar todos"),
			h("div", { class: "row" }, [
				isbn,
				h(
					"button",
					{
						class: "btn",
						onClick: () => {
							if (!isbn.value.trim()) return log("ISBN vacío", "err");
							byIsbn(isbn.value.trim());
						},
					},
					"Buscar ISBN"
				),
			]),
			h("div", { class: "row" }, [
				author,
				h(
					"button",
					{
						class: "btn",
						onClick: () => {
							if (!author.value.trim()) return log("Autor vacío", "err");
							byAuthor(author.value.trim());
						},
					},
					"Buscar autor"
				),
			]),
			h("div", { class: "row" }, [
				format,
				h(
					"button",
					{
						class: "btn",
						onClick: () => {
							if (!format.value.trim()) return log("Formato vacío", "err");
							byFormat(format.value.trim());
						},
					},
					"Buscar formato"
				),
			]),
		]),
		h("div", { class: "sep" }),
		h("div", { style: "overflow:auto" }, tbl),
	]);
}
function BooksInsert() {
	const f = {
		isbn: h("input", {}),
		titulo: h("input", {}),
		anio: h("input", { type: "number" }),
		precio: h("input", { type: "number", step: "0.01" }),
		stock: h("input", { type: "number" }),
		genero: h("input", { placeholder: "Debe existir" }),
		formato: h("input", { placeholder: "Debe existir" }),
		autor: h("input", { placeholder: "Separados por coma" }),
	};
	async function submit() {
		const payload = {
			isbn: f.isbn.value.trim(),
			titulo: f.titulo.value.trim(),
			anio_publicacion: +f.anio.value || null,
			precio: parseFloat(f.precio.value) || 0,
			stock: +f.stock.value || 0,
			genero: f.genero.value.trim(),
			formato: f.formato.value.trim(),
			autor: f.autor.value.trim(),
		};
		if (!payload.isbn || !payload.titulo) return log("Insertar: faltan campos clave", "err");
		const r = await fetch(state.booksBase + "/api/books/insert", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
		lastXML = await r.text();
		if (!r.ok) return log(`Insertar ERROR ${r.status}`, "err");
		log("Libro insertado");
	}
	return h("div", { class: "grid" }, [
		h("div", { class: "col-3" }, [h("label", {}, "ISBN"), f.isbn]),
		h("div", { class: "col-3" }, [h("label", {}, "Título"), f.titulo]),
		h("div", { class: "col-3" }, [h("label", {}, "Año"), f.anio]),
		h("div", { class: "col-3" }, [h("label", {}, "Precio"), f.precio]),
		h("div", { class: "col-3" }, [h("label", {}, "Stock"), f.stock]),
		h("div", { class: "col-3" }, [h("label", {}, "Género"), f.genero]),
		h("div", { class: "col-3" }, [h("label", {}, "Formato"), f.formato]),
		h("div", { class: "col-6" }, [h("label", {}, "Autor(es)"), f.autor]),
		h("div", { class: "col-12 row", style: "justify-content:flex-end;margin-top:8px" }, [h("button", { class: "btn ok", onClick: submit }, "Insertar")]),
	]);
}
function BooksUpdate() {
	const f = {
		isbn: h("input", {}),
		titulo: h("input", { placeholder: "(opcional)" }),
		anio: h("input", { type: "number", placeholder: "(opcional)" }),
		precio: h("input", { type: "number", step: "0.01", placeholder: "(opcional)" }),
		stock: h("input", { type: "number", placeholder: "(opcional)" }),
	};
	async function submit() {
		const body = {};
		const i = f.isbn.value.trim();
		if (!i) return log("Actualizar: ISBN vacío", "err");
		if (f.titulo.value.trim()) body.titulo = f.titulo.value.trim();
		if (f.anio.value.trim()) body.anio_publicacion = +f.anio.value;
		if (f.precio.value.trim()) body.precio = parseFloat(f.precio.value);
		if (f.stock.value.trim()) body.stock = +f.stock.value;
		if (!Object.keys(body).length) return log("Nada que actualizar", "err");
		const r = await fetch(state.booksBase + "/api/books/update/" + encodeURIComponent(i), {
			method: "PUT",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
		});
		lastXML = await r.text();
		r.ok ? log("Libro actualizado") : log(`Actualizar ERROR ${r.status}`, "err");
	}
	return h("div", { class: "grid" }, [
		h("div", { class: "col-3" }, [h("label", {}, "ISBN"), f.isbn]),
		h("div", { class: "col-3" }, [h("label", {}, "Título"), f.titulo]),
		h("div", { class: "col-3" }, [h("label", {}, "Año"), f.anio]),
		h("div", { class: "col-3" }, [h("label", {}, "Precio"), f.precio]),
		h("div", { class: "col-3" }, [h("label", {}, "Stock"), f.stock]),
		h("div", { class: "col-12 row", style: "justify-content:flex-end;margin-top:8px" }, [h("button", { class: "btn warn", onClick: submit }, "Actualizar")]),
	]);
}
function BooksDelete() {
	const input = h("input", { placeholder: "978-0307743657, 978-0000000000" });
	async function submit() {
		const list = input.value
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
		if (!list.length) return log("Borrar: lista vacía", "err");
		const r = await fetch(state.booksBase + "/api/books/delete", { method: "DELETE", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ isbns: list }) });
		lastXML = await r.text();
		r.ok ? log("Libros borrados") : log(`Borrar ERROR ${r.status}`, "err");
	}
	return h("div", { class: "grid" }, [
		h("div", { class: "col-8" }, [h("label", {}, "ISBNs separados por coma"), input]),
		h("div", { class: "col-4 row", style: "justify-content:flex-end;margin-top:8px" }, [h("button", { class: "btn danger", onClick: submit }, "Borrar")]),
	]);
}
function BooksRaw() {
	return h("pre", { class: "mono muted" }, lastXML);
}

// ====== Lógica de AUTH compartida ======
async function apiFetchAuth(path, opts = {}, retry = true) {
	const url = state.authBase + path;
	const headers = Object.assign({ "Content-Type": "application/json" }, opts.headers || {});
	if (state.access) headers["Authorization"] = "Bearer " + state.access;
	const res = await fetch(url, Object.assign({}, opts, { headers }));
	if (res.status === 401 && retry && state.refresh) {
		log(`401 en ${path}, intentando refresh...`, "warn");
		const ok = await doRefresh();
		if (ok) return apiFetchAuth(path, opts, false);
	}
	return res;
}
async function doRegister() {
	const email = $("#regEmail")?.value?.trim(),
		username = $("#regUser")?.value?.trim(),
		password = $("#regPass")?.value;
	if (!email || !username || !password) return log("Registro: faltan campos", "err");
	const r = await fetch(state.authBase + "/auth/register", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, username, password }) });
	const j = await r.json().catch(() => ({}));
	if (!r.ok) return log(`Registro ERROR ${r.status} ${json(j)}`, "err");
	state.access = j.tokens?.access_token || "";
	state.refresh = j.tokens?.refresh_token || "";
	saveState();
	log(`Registro OK user=${j.user?.username}`);
	render();
}
async function doLogin() {
	const who = $("#loginWho")?.value?.trim(),
		password = $("#loginPass")?.value;
	if (!who || !password) return log("Login: faltan campos", "err");
	const r = await fetch(state.authBase + "/auth/login", {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({ email: who, username: who, password }),
	});
	const j = await r.json().catch(() => ({}));
	if (!r.ok) return log(`Login ERROR ${r.status} ${json(j)}`, "err");
	state.access = j.tokens?.access_token || "";
	state.refresh = j.tokens?.refresh_token || "";
	saveState();
	log(`Login OK user=${j.user?.username}`);
	render();
}
async function doRefresh() {
	if (!state.refresh) {
		log("No hay refresh", "err");
		return false;
	}
	const r = await fetch(state.authBase + "/auth/refresh", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: state.refresh }) });
	const j = await r.json().catch(() => ({}));
	if (!r.ok) {
		log(`Refresh ERROR ${r.status} ${json(j)}`, "err");
		doLogout(true);
		return false;
	}
	state.access = j.access_token || "";
	saveState();
	log("Access renovado");
	render();
	return true;
}
function doLogout(silent = false) {
	state.access = "";
	state.refresh = "";
	saveState();
	if (!silent) log("Sesión cerrada");
	render();
}

// ====== Utiles extra ======
function escapeHtml(s) {
	return (s || "").replace(/[&<>"'`=\/]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;", "/": "&#x2F;", "`": "&#x60;", "=": "&#x3D;" }[c]));
}

// ====== Rutas ======
route("/", ViewHome);
route("/auth", ViewAuth);
route("/auth/register", ViewAuth);
route("/auth/login", ViewAuth);
route("/auth/tokens", ViewAuth);
route("/auth/profile", ViewAuth);
route("/auth/items", ViewAuth);
route("/books", ViewBooks);
route("/books/browse", ViewBooks);
route("/books/insert", ViewBooks);
route("/books/update", ViewBooks);
route("/books/delete", ViewBooks);
route("/books/raw", ViewBooks);
route("/404", () => h("div", { class: "card" }, [h("h2", {}, "404"), h("div", { class: "muted" }, "Ruta no encontrada")]));

// ====== Eventos globales ======
el("btn-logout").addEventListener("click", () => doLogout(false));

// Init
(function () {
	setAuthUI();
	render();
	log("Cliente listo: vistas separadas por servicio/acción.", "ok");
})();
