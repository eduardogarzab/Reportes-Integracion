// /js/utils.js — utilidades front CQRS

export const LS_KEY = "libros_cfg"; // coincide con resetCfg del app.js

export const defaults = {
	protocol: "http",
	host: "172.206.106.38",
	port: "5000",

	// Lecturas (QUERY)
	basePath: "/query",
	epAll: "/books",
	epIsbn: "/books/isbn/{isbn}",
	epFormat: "/books/format/{format}",
	epAuthor: "/books/author/{author}",

	// Escrituras (COMMAND) — solo paths relativos
	epInsert: "/books", // POST   /command/books
	epUpdate: "/books/{isbn}", // PUT    /command/books/{isbn}
	epDelete: "/books/delete", // DELETE /command/books/delete

	// XSL servido por el backend Flask (más simple que archivo local)
	xslPath: "/libros.xsl",
};

// ------------------ DOM helpers ------------------
export const qs = (sel, root = document) => root.querySelector(sel);
export const qsa = (sel, root = document) => [...root.querySelectorAll(sel)];
export function setText(node, msg, cls = "") {
	if (!node) return;
	node.textContent = msg || "";
	node.classList.remove("ok", "warn", "err");
	if (cls) node.classList.add(cls);
}

// ------------------ Config persistente ------------------
export function getCfg() {
	try {
		return JSON.parse(localStorage.getItem(LS_KEY) || "null") || { ...defaults };
	} catch {
		return { ...defaults };
	}
}
export function setCfg(obj) {
	localStorage.setItem(LS_KEY, JSON.stringify(obj || {}));
}

// ------------------ UUID / Idempotency-Key ------------------
export function uuidv4() {
	if (crypto && crypto.randomUUID) return crypto.randomUUID();
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0,
			v = c === "x" ? r : (r & 0x3) | 0x8;
		return v.toString(16);
	});
}

// ------------------ (Opcionales) Helpers de URL ------------------
export function normalizePath(p = "") {
	if (!p) return "";
	if (!p.startsWith("/")) p = "/" + p;
	return p.replace(/\/{2,}/g, "/");
}
function siblingCommandPath(queryBase = "/query") {
	const clean = normalizePath(queryBase || "/query");
	if (clean === "/query") return "/command";
	const replaced = clean.replace(/\/query\b/, "/command");
	return replaced === clean ? "/command" : replaced;
}
export function buildBaseURL(cfg) {
	const port = cfg.port ? `:${cfg.port}` : "";
	const base = cfg.basePath ? normalizePath(cfg.basePath) : "";
	return `${cfg.protocol}://${cfg.host}${port}${base}`;
}
function buildCommandBaseURL(cfg) {
	const port = cfg.port ? `:${cfg.port}` : "";
	const cmdBase = siblingCommandPath(cfg.basePath);
	return `${cfg.protocol}://${cfg.host}${port}${normalizePath(cmdBase)}`;
}
// Lecturas
export function buildURL_All(cfg) {
	return buildBaseURL(cfg) + normalizePath(cfg.epAll || "/books");
}
export function buildURL_Isbn(cfg, i) {
	return buildBaseURL(cfg) + normalizePath((cfg.epIsbn || "/books/isbn/{isbn}").replace("{isbn}", encodeURIComponent(i)));
}
export function buildURL_Format(cfg, f) {
	return buildBaseURL(cfg) + normalizePath((cfg.epFormat || "/books/format/{format}").replace("{format}", encodeURIComponent(f)));
}
export function buildURL_Author(cfg, a) {
	return buildBaseURL(cfg) + normalizePath((cfg.epAuthor || "/books/author/{author}").replace("{author}", encodeURIComponent(a)));
}
// Escrituras
export function buildURL_Insert(cfg) {
	return buildCommandBaseURL(cfg) + normalizePath(cfg.epInsert || "/books");
}
export function buildURL_Update(cfg, i) {
	return buildCommandBaseURL(cfg) + normalizePath((cfg.epUpdate || "/books/{isbn}").replace("{isbn}", encodeURIComponent(i)));
}
export function buildURL_Delete(cfg) {
	return buildCommandBaseURL(cfg) + normalizePath(cfg.epDelete || "/books/delete");
}

// ------------------ XML / XSL (por si los necesitas aquí también) ------------------
export async function fetchXML(url) {
	const res = await fetch(url, { headers: { Accept: "application/xml,text/xml;q=0.9,*/*;q=0.8" }, cache: "no-store" });
	const text = await res.text();
	if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText} — ${text.slice(0, 200)}`);
	const parser = new DOMParser();
	const xmlDoc = parser.parseFromString(text, "application/xml");
	if (xmlDoc.getElementsByTagName("parsererror").length) throw new Error("Respuesta XML mal formada (parsererror).");
	return { xmlDoc, xmlText: text };
}

let cachedXsl = null;
export async function getXslDoc(xslPath) {
	if (cachedXsl) return cachedXsl;
	const res = await fetch(xslPath, { cache: "reload", headers: { Accept: "application/xml,text/xml" } });
	const xslText = await res.text();
	const parser = new DOMParser();
	const xslDoc = parser.parseFromString(xslText, "application/xml");
	if (xslDoc.getElementsByTagName("parsererror").length) throw new Error("XSL inválido o mal formado");
	cachedXsl = xslDoc;
	return xslDoc;
}

export async function transformXML(xmlDoc, xslPath) {
	const xslDoc = await getXslDoc(xslPath);
	if (window.XSLTProcessor) {
		const proc = new XSLTProcessor();
		proc.importStylesheet(xslDoc);
		return proc.transformToFragment(xmlDoc, document);
	}
	const div = document.createElement("div");
	div.textContent = "Navegador sin soporte XSLT.";
	return div;
}

export function extractUnique(xmlDoc, xpathExpr) {
	const it = xmlDoc.evaluate(xpathExpr, xmlDoc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
	const s = new Set();
	for (let i = 0; i < it.snapshotLength; i++) {
		const v = (it.snapshotItem(i).textContent || "").trim();
		if (!v) continue;
		if (xpathExpr.includes("author")) {
			v.split(",")
				.map((x) => x.trim())
				.filter(Boolean)
				.forEach((x) => s.add(x));
		} else {
			s.add(v);
		}
	}
	return Array.from(s).sort((a, b) => a.localeCompare(b, "es"));
}
