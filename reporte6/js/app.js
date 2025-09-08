// /js/app.js
import { uuidv4, qs, qsa, setText, getCfg, setCfg } from "./utils.js";

const els = {
	cfgForm: qs("#cfgForm"),
	loadCfg: qs("#loadCfg"),
	resetCfg: qs("#resetCfg"),
	testPing: qs("#testPing"),
	statusCfg: qs("#statusCfg"),

	btnAll: qs("#btnAll"),
	btnIsbn: qs("#btnIsbn"),
	btnFormat: qs("#btnFormat"),
	btnAuthor: qs("#btnAuthor"),
	btnRefreshLists: qs("#btnRefreshLists"),
	statusReq: qs("#statusReq"),
	renderTarget: qs("#renderTarget"),
	xmlBox: qs("#xmlBox"),
	xmlRaw: qs("#xmlRaw"),
	btnToggleXML: qs("#btnToggleXML"),

	isbnInput: qs("#isbnInput"),
	formatSelect: qs("#formatSelect"),
	authorSelect: qs("#authorSelect"),

	formInsert: qs("#formInsert"),
	formUpdate: qs("#formUpdate"),
	formDelete: qs("#formDelete"),
	statusInsert: qs("#statusInsert"),
	statusUpdate: qs("#statusUpdate"),
	statusDelete: qs("#statusDelete"),
};

function normalizeBasePath(bp) {
	if (!bp) return "/query";
	if (!bp.startsWith("/")) bp = `/${bp}`;
	return bp;
}

// Dado el basePath de consultas (/query), devuelve el de comandos (/command)
function siblingCommandPath(queryBase) {
	const clean = normalizeBasePath(queryBase);
	if (clean === "/query") return "/command";
	return clean.replace(/\/query\b/, "/command");
}

function buildBaseURL(cfg) {
	const proto = cfg.protocol || "http";
	const host = cfg.host || "127.0.0.1";
	const port = cfg.port ? `:${cfg.port}` : "";
	return `${proto}://${host}${port}`;
}

function cfgFromForm() {
	const f = els.cfgForm;
	return {
		protocol: f.protocol.value || "http",
		host: f.host.value || "127.0.0.1",
		port: f.port.value || "",
		basePath: normalizeBasePath(f.basePath.value || "/query"),
		epAll: f.epAll.value || "/books",
		epIsbn: f.epIsbn.value || "/books/isbn/{isbn}",
		epFormat: f.epFormat.value || "/books/format/{format}",
		epAuthor: f.epAuthor.value || "/books/author/{author}",
	};
}

function paintCfg(cfg) {
	const f = els.cfgForm;
	f.protocol.value = cfg.protocol || "http";
	f.host.value = cfg.host || "";
	f.port.value = cfg.port || "";
	f.basePath.value = cfg.basePath || "/query";
	f.epAll.value = cfg.epAll || "/books";
	f.epIsbn.value = cfg.epIsbn || "/books/isbn/{isbn}";
	f.epFormat.value = cfg.epFormat || "/books/format/{format}";
	f.epAuthor.value = cfg.epAuthor || "/books/author/{author}";
}

function loadSavedCfg() {
	const cfg = getCfg();
	if (cfg) paintCfg(cfg);
}

function saveCfg(e) {
	e.preventDefault();
	const cfg = cfgFromForm();
	setCfg(cfg);
	setText(els.statusCfg, "✅ Configuración guardada.", "ok");
}

function resetCfg() {
	localStorage.removeItem("libros_cfg");
	paintCfg({ basePath: "/query" });
	setText(els.statusCfg, "⚠️ Configuración restablecida.", "warn");
}

async function fetchText(url, headers = {}) {
	const res = await fetch(url, { headers });
	const txt = await res.text();
	if (!res.ok) {
		const err = new Error(`HTTP ${res.status} ${res.statusText}`);
		err.payload = txt;
		throw err;
	}
	return txt;
}

function parseXML(text) {
	const doc = new window.DOMParser().parseFromString(text, "application/xml");
	const pe = doc.getElementsByTagName("parsererror");
	if (pe && pe.length) {
		const msg = pe[0].textContent || "XML mal formado";
		throw new Error(msg);
	}
	return doc;
}

async function fetchXML(url) {
	const txt = await fetchText(url, { Accept: "application/xml,text/xml" });
	els.xmlRaw.textContent = txt; // mostrar crudo
	return parseXML(txt);
}

async function fetchXSL(xslUrl) {
	const txt = await fetchText(xslUrl, { Accept: "application/xml,text/xml" });
	return parseXML(txt);
}

function transform(xmlDoc, xslDoc) {
	const proc = new XSLTProcessor();
	proc.importStylesheet(xslDoc);
	return proc.transformToFragment(xmlDoc, document);
}

// ----------------------- QUERIES (XML + XSL fragment) -----------------------
async function runQuery(urlBase, queryBase, ep) {
	const xmlUrl = `${urlBase}${queryBase}${ep}`;
	const xslUrl = `${urlBase}/libros_fragment.xsl`; // usamos el fragmento aislado

	try {
		setText(els.statusReq, "Cargando...", "");
		const xml = await fetchXML(xmlUrl);
		const xsl = await fetchXSL(xslUrl);

		const htmlFrag = transform(xml, xsl);
		els.renderTarget.innerHTML = "";
		els.renderTarget.appendChild(htmlFrag);
		setText(els.statusReq, "✅ OK", "ok");

		if (ep === "/books") refillListsFromXML(xml);
	} catch (e) {
		console.error("[runQuery] fallo:", e, e.payload || "");
		setText(els.statusReq, `❌ Error al consultar: ${String(e).slice(0, 160)}`, "err");
	}
}

function refillListsFromXML(xmlDoc) {
	const books = [...xmlDoc.querySelectorAll("catalog > book")];
	const formats = new Set();
	const authors = new Set();
	books.forEach((b) => {
		const f = b.querySelector("format")?.textContent?.trim();
		if (f) formats.add(f);
		const a = b.querySelector("author")?.textContent?.trim();
		if (a)
			a.split(",")
				.map((s) => s.trim())
				.filter(Boolean)
				.forEach((v) => authors.add(v));
	});
	els.formatSelect.innerHTML = `<option value="">— seleccionar —</option>` + [...formats].map((f) => `<option>${f}</option>`).join("");
	els.authorSelect.innerHTML = `<option value="">— seleccionar —</option>` + [...authors].map((a) => `<option>${a}</option>`).join("");
}

// ----------------------- COMMANDS (JSON + XML response) -----------------------
async function sendCommand(urlBase, commandBase, path, method, bodyObj, statusEl) {
	try {
		setText(statusEl, "Enviando...", "");
		const idem = uuidv4();
		const res = await fetch(`${urlBase}${commandBase}${path}`, {
			method,
			headers: {
				"Content-Type": "application/json",
				Accept: "application/xml,text/xml",
				"Idempotency-Key": idem,
			},
			body: bodyObj ? JSON.stringify(bodyObj) : null,
		});
		const txt = await res.text(); // la API devuelve XML (mensaje)
		els.xmlRaw.textContent = txt; // muestra crudo
		setText(statusEl, `Respuesta (${res.status})`, res.ok ? "ok" : "err");
		if (res.ok) {
			const cfg = cfgFromForm();
			await runQuery(buildBaseURL(cfg), cfg.basePath, cfg.epAll);
		}
	} catch (e) {
		console.error(e);
		setText(statusEl, "❌ Error en command.", "err");
	}
}

// ----------------------- UI Events -----------------------
function wire() {
	// CFG
	els.cfgForm.addEventListener("submit", saveCfg);
	els.loadCfg.addEventListener("click", loadSavedCfg);
	els.resetCfg.addEventListener("click", resetCfg);

	els.testPing.addEventListener("click", async () => {
		const cfg = cfgFromForm();
		await runQuery(buildBaseURL(cfg), cfg.basePath, cfg.epAll);
	});

	// Queries
	els.btnAll.addEventListener("click", async () => {
		const cfg = cfgFromForm();
		await runQuery(buildBaseURL(cfg), cfg.basePath, cfg.epAll);
	});

	els.btnIsbn.addEventListener("click", async () => {
		const cfg = cfgFromForm();
		const isbn = (els.isbnInput.value || "").trim();
		if (!isbn) return setText(els.statusReq, "Proporciona un ISBN.", "warn");
		const ep = cfg.epIsbn.replace("{isbn}", encodeURIComponent(isbn));
		await runQuery(buildBaseURL(cfg), cfg.basePath, ep);
	});

	els.btnFormat.addEventListener("click", async () => {
		const cfg = cfgFromForm();
		const fmt = els.formatSelect.value.trim();
		if (!fmt) return setText(els.statusReq, "Selecciona un formato.", "warn");
		const ep = cfg.epFormat.replace("{format}", encodeURIComponent(fmt));
		await runQuery(buildBaseURL(cfg), cfg.basePath, ep);
	});

	els.btnAuthor.addEventListener("click", async () => {
		const cfg = cfgFromForm();
		const author = els.authorSelect.value.trim();
		if (!author) return setText(els.statusReq, "Selecciona un autor.", "warn");
		const ep = cfg.epAuthor.replace("{author}", encodeURIComponent(author));
		await runQuery(buildBaseURL(cfg), cfg.basePath, ep);
	});

	els.btnRefreshLists.addEventListener("click", async () => {
		const cfg = cfgFromForm();
		await runQuery(buildBaseURL(cfg), cfg.basePath, cfg.epAll);
	});

	els.btnToggleXML.addEventListener("click", () => {
		const open = els.xmlBox.hasAttribute("open");
		if (open) els.xmlBox.removeAttribute("open");
		else els.xmlBox.setAttribute("open", "true");
		els.btnToggleXML.setAttribute("aria-expanded", String(!open));
	});

	// Commands
	els.formInsert.addEventListener("submit", async (e) => {
		e.preventDefault();
		const cfg = cfgFromForm();
		const cmdBase = siblingCommandPath(cfg.basePath);
		const body = {
			isbn: qs("#insIsbn").value.trim(),
			titulo: qs("#insTitulo").value.trim(),
			anio_publicacion: Number(qs("#insAnio").value),
			precio: Number(qs("#insPrecio").value),
			stock: Number(qs("#insStock").value),
			genero: qs("#insGenero").value.trim(),
			formato: qs("#insFormato").value.trim(),
			autor: qs("#insAutor").value.trim(),
		};
		await sendCommand(buildBaseURL(cfg), cmdBase, "/books", "POST", body, els.statusInsert);
	});

	els.formUpdate.addEventListener("submit", async (e) => {
		e.preventDefault();
		const cfg = cfgFromForm();
		const cmdBase = siblingCommandPath(cfg.basePath);
		const isbn = qs("#updIsbn").value.trim();
		if (!isbn) return setText(els.statusUpdate, "Falta ISBN.", "warn");
		const body = {};
		const t = qs("#updTitulo").value.trim();
		if (t) body.titulo = t;
		const a = qs("#updAnio").value;
		if (a) body.anio_publicacion = Number(a);
		const p = qs("#updPrecio").value;
		if (p) body.precio = Number(p);
		const s = qs("#updStock").value;
		if (s) body.stock = Number(s);
		await sendCommand(buildBaseURL(cfg), cmdBase, `/books/${encodeURIComponent(isbn)}`, "PUT", body, els.statusUpdate);
	});

	els.formDelete.addEventListener("submit", async (e) => {
		e.preventDefault();
		const cfg = cfgFromForm();
		const cmdBase = siblingCommandPath(cfg.basePath);
		const raw = qs("#delIsbns").value.trim();
		if (!raw) return setText(els.statusDelete, "Proporciona una lista de ISBNs.", "warn");
		const isbns = raw
			.split(",")
			.map((s) => s.trim())
			.filter(Boolean);
		await sendCommand(buildBaseURL(cfg), cmdBase, "/books/delete", "DELETE", { isbns }, els.statusDelete);
	});
}

(function init() {
	loadSavedCfg();
	wire();
})();
