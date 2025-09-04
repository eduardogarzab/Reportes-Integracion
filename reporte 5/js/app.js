// js/app.js
import {
  defaults, normalizePath, buildURL_All, buildURL_Isbn, buildURL_Format, buildURL_Author,
  buildURL_Insert, buildURL_Update, buildURL_Delete,
  loadConfig, saveConfig, fetchXML, transformXML, extractUnique,
  postJson, putJson, deleteJson
} from "./utils.js";

const els = {
  // Config
  cfgForm: document.getElementById("cfgForm"),
  protocol: document.getElementById("protocol"),
  host: document.getElementById("host"),
  port: document.getElementById("port"),
  basePath: document.getElementById("basePath"),
  epAll: document.getElementById("epAll"),
  epIsbn: document.getElementById("epIsbn"),
  epFormat: document.getElementById("epFormat"),
  epAuthor: document.getElementById("epAuthor"),
  loadCfg: document.getElementById("loadCfg"),
  resetCfg: document.getElementById("resetCfg"),
  testPing: document.getElementById("testPing"),
  statusCfg: document.getElementById("statusCfg"),

  // Browse / filters
  isbnInput: document.getElementById("isbnInput"),
  authorSelect: document.getElementById("authorSelect"),
  formatSelect: document.getElementById("formatSelect"),
  btnAll: document.getElementById("btnAll"),
  btnIsbn: document.getElementById("btnIsbn"),
  btnFormat: document.getElementById("btnFormat"),
  btnAuthor: document.getElementById("btnAuthor"),
  btnToggleXML: document.getElementById("btnToggleXML"),
  btnRefreshLists: document.getElementById("btnRefreshLists"),
  statusReq: document.getElementById("statusReq"),
  renderTarget: document.getElementById("renderTarget"),
  xmlBox: document.getElementById("xmlBox"),
  xmlRaw: document.getElementById("xmlRaw"),

  // CRUD
  formInsert: document.getElementById("formInsert"),
  insIsbn: document.getElementById("insIsbn"),
  insTitulo: document.getElementById("insTitulo"),
  insAnio: document.getElementById("insAnio"),
  insPrecio: document.getElementById("insPrecio"),
  insStock: document.getElementById("insStock"),
  insGenero: document.getElementById("insGenero"),
  insFormato: document.getElementById("insFormato"),
  insAutor: document.getElementById("insAutor"),
  statusInsert: document.getElementById("statusInsert"),

  formUpdate: document.getElementById("formUpdate"),
  updIsbn: document.getElementById("updIsbn"),
  updTitulo: document.getElementById("updTitulo"),
  updAnio: document.getElementById("updAnio"),
  updPrecio: document.getElementById("updPrecio"),
  updStock: document.getElementById("updStock"),
  statusUpdate: document.getElementById("statusUpdate"),

  formDelete: document.getElementById("formDelete"),
  delIsbns: document.getElementById("delIsbns"),
  statusDelete: document.getElementById("statusDelete"),
};

function setStatus(el, type, msg) {
  el.className = "status " + (type || "muted");
  el.textContent = msg;
}

function readFormToConfig() {
  return {
    protocol: els.protocol.value.trim() || defaults.protocol,
    host: els.host.value.trim(),
    port: els.port.value.trim(),
    basePath: normalizePath(els.basePath.value.trim() || defaults.basePath),
    epAll: normalizePath(els.epAll.value.trim() || defaults.epAll),
    epIsbn: normalizePath(els.epIsbn.value.trim() || defaults.epIsbn),
    epFormat: normalizePath(els.epFormat.value.trim() || defaults.epFormat),
    epAuthor: normalizePath(els.epAuthor.value.trim() || defaults.epAuthor),
    epInsert: defaults.epInsert,
    epUpdate: defaults.epUpdate,
    epDelete: defaults.epDelete,
    xslPath: defaults.xslPath,
  };
}

function populateForm(cfg) {
  els.protocol.value = cfg.protocol || defaults.protocol;
  els.host.value = cfg.host || "";
  els.port.value = cfg.port || "";
  els.basePath.value = cfg.basePath || defaults.basePath;
  els.epAll.value = cfg.epAll || defaults.epAll;
  els.epIsbn.value = cfg.epIsbn || defaults.epIsbn;
  els.epFormat.value = cfg.epFormat || defaults.epFormat;
  els.epAuthor.value = cfg.epAuthor || defaults.epAuthor;
}

async function renderFromURL(url) {
  setStatus(els.statusReq, "muted", `Consultando: ${url}`);
  const { xmlDoc, xmlText } = await fetchXML(url);
  els.xmlRaw.textContent = xmlText;
  const frag = await transformXML(xmlDoc, readFormToConfig().xslPath);
  els.renderTarget.innerHTML = "";
  els.renderTarget.appendChild(frag);
  setStatus(els.statusReq, "ok", "Datos cargados y transformados correctamente.");
  return xmlDoc;
}

async function doQuery(kind) {
  const cfg = readFormToConfig();
  saveConfig(cfg);
  let url = "";

  if (kind === "all") {
    url = buildURL_All(cfg);
  } else if (kind === "isbn") {
    const v = els.isbnInput.value.trim();
    if (!v) throw new Error("Ingresa un ISBN.");
    url = buildURL_Isbn(cfg, v);
  } else if (kind === "format") {
    const v = els.formatSelect.value.trim();
    if (!v) throw new Error("Selecciona un formato.");
    url = buildURL_Format(cfg, v);
  } else if (kind === "author") {
    const v = els.authorSelect.value.trim();
    if (!v) throw new Error("Selecciona un autor.");
    url = buildURL_Author(cfg, v);
  }

  try {
    await renderFromURL(url);
  } catch (err) {
    els.renderTarget.innerHTML = "";
    setStatus(els.statusReq, "err", `Error: ${err.message}`);
  }
}

// Alimenta selects de Formato y Autor a partir de /api/books
async function refreshLists() {
  const cfg = readFormToConfig();
  saveConfig(cfg);

  try {
    const { xmlDoc } = await fetchXML(buildURL_All(cfg));
    const formats = extractUnique(xmlDoc, "/catalog/book/format");
    const authors = extractUnique(xmlDoc, "/catalog/book/author");

    // Formatos
    els.formatSelect.innerHTML = `<option value="">— seleccionar —</option>` +
      formats.map(f => `<option value="${escapeHtml(f)}">${escapeHtml(f)}</option>`).join("");

    // Autores
    els.authorSelect.innerHTML = `<option value="">— seleccionar —</option>` +
      authors.map(a => `<option value="${escapeHtml(a)}">${escapeHtml(a)}</option>`).join("");

    setStatus(els.statusReq, "ok", "Listas de Formato/Autor actualizadas.");
  } catch (err) {
    setStatus(els.statusReq, "err", `No pude actualizar listas: ${err.message}`);
  }
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
}

// ====== Eventos de Config ======
els.cfgForm.addEventListener("submit", (e) => {
  e.preventDefault();
  saveConfig(readFormToConfig());
  setStatus(els.statusCfg, "ok", "Configuración guardada en localStorage.");
});

els.loadCfg.addEventListener("click", () => {
  const cfg = loadConfig();
  populateForm(cfg);
  setStatus(els.statusCfg, "muted", "Configuración cargada.");
});

els.resetCfg.addEventListener("click", () => {
  saveConfig({ ...defaults });
  populateForm({ ...defaults });
  setStatus(els.statusCfg, "warn", "Valores restablecidos a los predeterminados.");
});

els.testPing.addEventListener("click", async () => {
  const cfg = readFormToConfig();
  saveConfig(cfg);
  const url = buildURL_All(cfg);
  setStatus(els.statusCfg, "muted", `Probando: ${url}`);
  try {
    const { xmlDoc } = await fetchXML(url);
    const count = xmlDoc.evaluate("count(/catalog/book)", xmlDoc, null, XPathResult.NUMBER_TYPE, null).numberValue;
    setStatus(els.statusCfg, "ok", `Conexión OK. Libros detectados: ${count}.`);
  } catch (err) {
    setStatus(els.statusCfg, "err", `Fallo al conectar: ${err.message}`);
  }
});

// ====== Eventos de Filtros ======
els.btnAll.addEventListener("click", () => doQuery("all"));
els.btnIsbn.addEventListener("click", () => doQuery("isbn"));
els.btnFormat.addEventListener("click", () => doQuery("format"));
els.btnAuthor.addEventListener("click", () => doQuery("author"));

let xmlVisible = false;
els.btnToggleXML.addEventListener("click", () => {
  xmlVisible = !xmlVisible;
  els.xmlBox.open = xmlVisible;
  els.btnToggleXML.setAttribute("aria-expanded", String(xmlVisible));
});

els.btnRefreshLists.addEventListener("click", refreshLists);

// ====== CRUD ======
els.formInsert.addEventListener("submit", async (e) => {
  e.preventDefault();
  const cfg = readFormToConfig(); saveConfig(cfg);
  const body = {
    isbn: els.insIsbn.value.trim(),
    titulo: els.insTitulo.value.trim(),
    anio_publicacion: Number(els.insAnio.value),
    precio: Number(els.insPrecio.value),
    stock: Number(els.insStock.value),
    genero: els.insGenero.value.trim(),
    formato: els.insFormato.value.trim(),
    autor: els.insAutor.value.trim() // “A, B, C” (deben existir)
  };
  try {
    const xmlText = await postJson(buildURL_Insert(cfg), body);
    setStatus(els.statusInsert, "ok", "Insertado. Revisa la respuesta en XML (abre ‘Mostrar XML’ si quieres).");
    // opcional: refrescar listados
  } catch (err) {
    setStatus(els.statusInsert, "err", `Error al insertar: ${err.message}`);
  }
});

els.formUpdate.addEventListener("submit", async (e) => {
  e.preventDefault();
  const cfg = readFormToConfig(); saveConfig(cfg);
  const isbnTarget = els.updIsbn.value.trim();
  const body = {};
  if (els.updTitulo.value.trim()) body.titulo = els.updTitulo.value.trim();
  if (els.updAnio.value.trim()) body.anio_publicacion = Number(els.updAnio.value);
  if (els.updPrecio.value.trim()) body.precio = Number(els.updPrecio.value);
  if (els.updStock.value.trim()) body.stock = Number(els.updStock.value);

  if (!isbnTarget) {
    setStatus(els.statusUpdate, "err", "Debes indicar el ISBN objetivo.");
    return;
  }
  if (Object.keys(body).length === 0) {
    setStatus(els.statusUpdate, "warn", "No hay cambios a enviar.");
    return;
  }

  try {
    const xmlText = await putJson(buildURL_Update(cfg, isbnTarget), body);
    setStatus(els.statusUpdate, "ok", "Actualizado. Revisa la respuesta en XML.");
  } catch (err) {
    setStatus(els.statusUpdate, "err", `Error al actualizar: ${err.message}`);
  }
});

els.formDelete.addEventListener("submit", async (e) => {
  e.preventDefault();
  const cfg = readFormToConfig(); saveConfig(cfg);
  const raw = els.delIsbns.value.trim();
  const isbns = raw ? raw.split(",").map(s => s.trim()).filter(Boolean) : [];
  if (isbns.length === 0) {
    setStatus(els.statusDelete, "err", "Indica al menos un ISBN.");
    return;
  }
  try {
    const xmlText = await deleteJson(buildURL_Delete(cfg), { isbns });
    setStatus(els.statusDelete, "ok", "Borrado realizado. Revisa la respuesta en XML.");
  } catch (err) {
    setStatus(els.statusDelete, "err", `Error al borrar: ${err.message}`);
  }
});

// ====== Init ======
(async function init() {
  const cfg = loadConfig();
  populateForm(cfg);
  setStatus(els.statusCfg, "muted", "Config inicial lista. Ajusta y guarda si es necesario.");
  els.xmlBox.open = false;

  // Intenta cargar listas (Formato/Autor) al inicio sin bloquear si falla
  try { await refreshLists(); } catch {}
})();
