// js/utils.js
export const LS_KEY = "librosAppConfig";

export const defaults = {
  protocol: "http",
  host: "172.206.106.38",
  port: "5000",
  basePath: "/api",
  epAll: "/books",
  epIsbn: "/books/isbn/{isbn}",
  epFormat: "/books/format/{format}",
  epAuthor: "/books/author/{author}",
  epInsert: "/books/insert",
  epUpdate: "/books/update/{isbn}",
  epDelete: "/books/delete",
  xslPath: "./xsl/libros.xsl"
};

export function normalizePath(p = "") {
  if (!p) return "";
  if (!p.startsWith("/")) p = "/" + p;
  return p.replace(/\/{2,}/g, "/");
}

export function buildBaseURL(cfg) {
  const port = cfg.port ? `:${cfg.port}` : "";
  const base = cfg.basePath ? normalizePath(cfg.basePath) : "";
  return `${cfg.protocol}://${cfg.host}${port}${base}`;
}

export function buildURL_All(cfg) {
  return buildBaseURL(cfg) + normalizePath(cfg.epAll || "/books");
}

export function buildURL_Isbn(cfg, isbn) {
  const ep = (cfg.epIsbn || "/books/isbn/{isbn}").replace("{isbn}", encodeURIComponent(isbn));
  return buildBaseURL(cfg) + normalizePath(ep);
}

export function buildURL_Format(cfg, format) {
  const ep = (cfg.epFormat || "/books/format/{format}").replace("{format}", encodeURIComponent(format));
  return buildBaseURL(cfg) + normalizePath(ep);
}

export function buildURL_Author(cfg, author) {
  const ep = (cfg.epAuthor || "/books/author/{author}").replace("{author}", encodeURIComponent(author));
  return buildBaseURL(cfg) + normalizePath(ep);
}

export function buildURL_Insert(cfg) {
  return buildBaseURL(cfg) + normalizePath(cfg.epInsert || "/books/insert");
}

export function buildURL_Update(cfg, isbn) {
  const ep = (cfg.epUpdate || "/books/update/{isbn}").replace("{isbn}", encodeURIComponent(isbn));
  return buildBaseURL(cfg) + normalizePath(ep);
}

export function buildURL_Delete(cfg) {
  return buildBaseURL(cfg) + normalizePath(cfg.epDelete || "/books/delete");
}

export function loadConfig() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || "null") || { ...defaults };
  } catch {
    return { ...defaults };
  }
}

export function saveConfig(cfg) {
  localStorage.setItem(LS_KEY, JSON.stringify(cfg));
}

export async function fetchXML(url) {
  const res = await fetch(url, {
    headers: { "Accept": "application/xml,text/xml;q=0.9,*/*;q=0.8" },
    cache: "no-store"
  });
  const text = await res.text();
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText} — ${text.slice(0, 200)}`);
  }
  const parser = new DOMParser();
  const xmlDoc = parser.parseFromString(text, "application/xml");
  if (xmlDoc.getElementsByTagName("parsererror").length) {
    throw new Error("Respuesta XML mal formada (parsererror).");
  }
  return { xmlDoc, xmlText: text };
}

// Carga XSL una sola vez
let cachedXsl = null;
export async function getXslDoc(xslPath) {
  if (cachedXsl) return cachedXsl;
  const res = await fetch(xslPath, { cache: "reload" });
  const xslText = await res.text();
  const parser = new DOMParser();
  const xslDoc = parser.parseFromString(xslText, "application/xml");
  if (xslDoc.getElementsByTagName("parsererror").length) {
    throw new Error("XSL inválido o mal formado");
  }
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

/** Extrae valores únicos de un XPath simple dentro del XML */
export function extractUnique(xmlDoc, xpathExpr) {
  const it = xmlDoc.evaluate(xpathExpr, xmlDoc, null, XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null);
  const s = new Set();
  for (let i = 0; i < it.snapshotLength; i++) {
    const v = (it.snapshotItem(i).textContent || "").trim();
    if (!v) continue;
    // Para autores, pueden venir "A, B, C"
    if (xpathExpr.includes("author")) {
      v.split(",").map(x => x.trim()).filter(Boolean).forEach(x => s.add(x));
    } else {
      s.add(v);
    }
  }
  return Array.from(s).sort((a, b) => a.localeCompare(b, "es"));
}

/** Helpers JSON (para insert/update/delete, el API responde XML) */
export async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/xml" },
    body: JSON.stringify(body)
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText} — ${text.slice(0,200)}`);
  return text; // XML de respuesta
}

export async function putJson(url, body) {
  const res = await fetch(url, {
    method: "PUT",
    headers: { "Content-Type": "application/json", "Accept": "application/xml" },
    body: JSON.stringify(body)
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText} — ${text.slice(0,200)}`);
  return text;
}

export async function deleteJson(url, body) {
  const res = await fetch(url, {
    method: "DELETE",
    headers: { "Content-Type": "application/json", "Accept": "application/xml" },
    body: JSON.stringify(body)
  });
  const text = await res.text();
  if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText} — ${text.slice(0,200)}`);
  return text;
}
