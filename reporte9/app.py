"""
TkClient – Escritorio para tus microservicios (Auth @ :5001 y Libros @ :5000)

Cambios solicitados:
1) Sección de **login** (usuario/contraseña)
2) Sección de **registro**
3) Sección para **refrescar token**
4) Sección de **config persistente** ("localStorage" de escritorio) para IP/puertos/endpoints
5) Sección para **consultar endpoint protegido** con el token
6) **Semáforo** de estado: verde (OK), naranja (en proceso), rojo (fuera de servicio) por servicio
7) Botones y colores claros
8) Mostrar siempre **peticiones, respuestas y JWT** en la GUI

Requisitos:
  pip install requests

Ejecución:
  python tkclient.py
"""

import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import requests
import datetime as dt
import xml.etree.ElementTree as ET
from pathlib import Path

# =============================
# Config persistente ("localStorage" desktop)
# =============================
class Config:
    def __init__(self, path: Path):
        self.path = path
        self.data = {
            "auth_base": "http://127.0.0.1:5001",
            "books_base": "http://127.0.0.1:5000"
        }
        self.load()

    def load(self):
        try:
            if self.path.exists():
                self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
        except Exception:
            pass

    def save(self):
        try:
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"No se pudo guardar config: {e}")

# =============================
# Cliente HTTP
# =============================
class ApiClient:
    def __init__(self, auth_base: str, books_base: str, logger=None):
        self.auth_base = auth_base.rstrip('/')
        self.books_base = books_base.rstrip('/')
        self.access_token = None
        self.access_exp = None
        self.refresh_token = None
        self.logger = logger

    def set_bases(self, auth_base: str, books_base: str):
        self.auth_base = auth_base.rstrip('/')
        self.books_base = books_base.rstrip('/')

    # ---- helpers ----
    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"} if self.access_token else {}

    def _raise_with_body(self, resp: requests.Response):
        body = None
        try:
            body = resp.text
        except Exception:
            body = "<no body>"
        raise requests.HTTPError(f"{resp.status_code} {resp.reason}: {resp.url}\nBody: {body}")

    def _log_io(self, label: str, url: str, method: str, payload=None, headers=None, resp=None):
        if not self.logger:
            return
        self.logger(f"[{label}] {method} {url}")
        if headers:
            red = dict(headers)
            if 'Authorization' in red:
                red['Authorization'] = 'Bearer ***REDACTED***'
            self.logger(f"  headers={red}")
        if payload is not None:
            self.logger(f"  payload={payload}")
        if resp is not None:
            try:
                ct = resp.headers.get('Content-Type','')
            except Exception:
                ct = ''
            self.logger(f"  => {resp.status_code} {resp.reason} content-type={ct}")
            try:
                text = resp.text
                self.logger(f"  body={text[:2000]}" + ("…" if len(text) > 2000 else ""))
            except Exception:
                pass

    # ---- AUTH API ----
    def register(self, email: str, username: str, password: str):
        url = f"{self.auth_base}/auth/register"
        payload = {"email": email, "username": username, "password": password}
        self._log_io("register", url, "POST", payload=payload)
        resp = requests.post(url, json=payload, timeout=10)
        self._log_io("register", url, "POST", payload=payload, resp=resp)
        if resp.status_code >= 400:
            self._raise_with_body(resp)
        data = resp.json()
        self._store_tokens_from_register_or_login(data)
        return data

    def login(self, who: str, password: str):
        url = f"{self.auth_base}/auth/login"
        payload = {"email": who, "username": who, "password": password}
        self._log_io("login", url, "POST", payload=payload)
        resp = requests.post(url, json=payload, timeout=10)
        self._log_io("login", url, "POST", payload=payload, resp=resp)
        if resp.status_code >= 400:
            self._raise_with_body(resp)
        data = resp.json()
        self._store_tokens_from_register_or_login(data)
        return data

    def _store_tokens_from_register_or_login(self, data: dict):
        toks = data.get("tokens", {})
        self.access_token = toks.get("access_token")
        self.refresh_token = toks.get("refresh_token")
        self.access_exp = toks.get("access_expires_at_utc")

    def refresh(self):
        if not self.refresh_token:
            raise RuntimeError("No hay refresh_token cargado.")
        url = f"{self.auth_base}/auth/refresh"
        payload = {"refresh_token": self.refresh_token}
        self._log_io("refresh", url, "POST", payload=payload)
        resp = requests.post(url, json=payload, timeout=10)
        self._log_io("refresh", url, "POST", payload=payload, resp=resp)
        if resp.status_code >= 400:
            self._raise_with_body(resp)
        data = resp.json()
        self.access_token = data.get("access_token")
        self.access_exp = data.get("access_expires_at_utc")
        return data

    def profile(self):
        url = f"{self.auth_base}/api/profile"
        headers = self._auth_headers()
        self._log_io("profile", url, "GET", headers=headers)
        resp = requests.get(url, headers=headers, timeout=10)
        self._log_io("profile", url, "GET", headers=headers, resp=resp)
        if resp.status_code >= 400:
            self._raise_with_body(resp)
        return resp.json()

    def health_auth(self):
        url = f"{self.auth_base}/health"
        self._log_io("health_auth", url, "GET")
        try:
            resp = requests.get(url, timeout=6)
            self._log_io("health_auth", url, "GET", resp=resp)
            return resp.status_code == 200
        except Exception as e:
            if self.logger:
                self.logger(f"health_auth error: {e}")
            return False

    # ---- BOOKS API (XML) ----
    def books_all(self):
        url = f"{self.books_base}/api/books"
        self._log_io("books_all", url, "GET")
        resp = requests.get(url, timeout=10, headers={"Accept": "application/xml"})
        self._log_io("books_all", url, "GET", resp=resp)
        if resp.status_code >= 400:
            self._raise_with_body(resp)
        return resp.text

    def health_books(self):
        # No hay /health en Libros; probamos /api/books
        try:
            txt = self.books_all()
            return bool(txt)
        except Exception:
            return False

# =============================
# UI principal (Tkinter + ttk)
# =============================
class Semaphore(tk.Canvas):
    def __init__(self, master, diameter=16, **kw):
        super().__init__(master, width=diameter+4, height=diameter+4, highlightthickness=0, **kw)
        self.d = diameter
        self.oval = self.create_oval(2, 2, 2+diameter, 2+diameter, fill="#aaa", outline="#666")
    def set(self, state: str):
        # 'green' | 'orange' | 'red' | 'gray'
        colors = {
            'green': '#16a34a',
            'orange': '#f59e0b',
            'red': '#ef4444',
            'gray': '#9ca3af'
        }
        self.itemconfig(self.oval, fill=colors.get(state, '#9ca3af'))

class TkClient(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TkClient – Auth + Libros")
        self.geometry("1200x800")
        self.minsize(1100, 720)

        # Config persistente
        cfg_path = Path.home() / ".tkclient_config.json"
        self.cfg = Config(cfg_path)

        # Estado
        self.client = ApiClient(self.cfg.data['auth_base'], self.cfg.data['books_base'], logger=self._log)

        # Layout raíz
        self._build_topbar()
        self._build_body()
        self._build_log()
        self._update_status()

    # ---------- top bar (config persistente + semáforos) ----------
    def _build_topbar(self):
        bar = ttk.Frame(self)
        bar.pack(side=tk.TOP, fill=tk.X, padx=8, pady=6)

        ttk.Label(bar, text="AUTH_BASE:").pack(side=tk.LEFT)
        self.var_auth = tk.StringVar(value=self.client.auth_base)
        ttk.Entry(bar, textvariable=self.var_auth, width=42).pack(side=tk.LEFT, padx=4)

        ttk.Label(bar, text="BOOKS_BASE:").pack(side=tk.LEFT, padx=(10,0))
        self.var_books = tk.StringVar(value=self.client.books_base)
        ttk.Entry(bar, textvariable=self.var_books, width=42).pack(side=tk.LEFT, padx=4)

        ttk.Button(bar, text="Aplicar y Guardar", command=self.apply_and_save_bases).pack(side=tk.LEFT, padx=8)
        ttk.Button(bar, text="Probar salud", command=self.check_health).pack(side=tk.LEFT)

        # Semáforos
        wrap = ttk.Frame(bar)
        wrap.pack(side=tk.RIGHT)
        row = ttk.Frame(wrap)
        row.pack()
        ttk.Label(row, text="AUTH").pack(side=tk.LEFT, padx=(0,4))
        self.sem_auth = Semaphore(row)
        self.sem_auth.pack(side=tk.LEFT, padx=(0,8))
        ttk.Label(row, text="BOOKS").pack(side=tk.LEFT, padx=(0,4))
        self.sem_books = Semaphore(row)
        self.sem_books.pack(side=tk.LEFT)
        self.sem_auth.set('gray'); self.sem_books.set('gray')

    def apply_and_save_bases(self):
        self.client.set_bases(self.var_auth.get(), self.var_books.get())
        self.cfg.data['auth_base'] = self.client.auth_base
        self.cfg.data['books_base'] = self.client.books_base
        self.cfg.save()
        self.log(f"Nuevas bases (guardadas): AUTH={self.client.auth_base} BOOKS={self.client.books_base}")

    def check_health(self):
        def worker():
            self.sem_auth.set('orange'); self.sem_books.set('orange')
            a = self.client.health_auth()
            self.sem_auth.set('green' if a else 'red')
            b = self.client.health_books()
            self.sem_books.set('green' if b else 'red')
            self.log(f"Health AUTH={a} BOOKS={b}")
        threading.Thread(target=worker, daemon=True).start()

    # ---------- cuerpo con tabs ----------
    def _build_body(self):
        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0,6))

        self.tab_auth = ttk.Frame(self.tabs)
        self.tab_protected = ttk.Frame(self.tabs)
        self.tab_books = ttk.Frame(self.tabs)

        self.tabs.add(self.tab_auth, text="Auth: Login/Registro/Token")
        self.tabs.add(self.tab_protected, text="Protegido (/api/profile)")
        self.tabs.add(self.tab_books, text="Libros (XML)")

        self._build_auth_tab()
        self._build_protected_tab()
        self._build_books_tab()

    # ---------- log panel ----------
    def _build_log(self):
        box = ttk.Frame(self)
        box.pack(side=tk.BOTTOM, fill=tk.BOTH, padx=8, pady=(0,8))
        ttk.Label(box, text="Peticiones y Respuestas (incluye JWT)").pack(anchor="w")
        self.txt_log = tk.Text(box, height=10)
        self.txt_log.pack(fill=tk.BOTH, expand=True)

    def _log(self, msg: str):
        ts = dt.datetime.now().strftime('%H:%M:%S')
        self.txt_log.insert(tk.END, f"[{ts}] {msg}\n")
        self.txt_log.see(tk.END)

    def log(self, msg: str):
        self._log(msg)

    def error(self, msg: str):
        self._log(f"ERROR: {msg}")
        self.bell()

    def _update_status(self):
        if self.client.access_token:
            exp = self.client.access_exp or "?"
            self.lbl_status.config(text=f"Autenticado • exp {exp}")
            self.txt_access.delete("1.0", tk.END); self.txt_access.insert(tk.END, self.client.access_token or "")
            self.txt_refresh.delete("1.0", tk.END); self.txt_refresh.insert(tk.END, self.client.refresh_token or "")
            self.txt_exp.delete(0, tk.END); self.txt_exp.insert(0, exp)
        else:
            self.lbl_status.config(text="Desconectado")
            self.txt_access.delete("1.0", tk.END)
            self.txt_refresh.delete("1.0", tk.END)
            self.txt_exp.delete(0, tk.END)

    # ================= AUTH TAB =================
    def _build_auth_tab(self):
        f = self.tab_auth
        pad = {"padx": 8, "pady": 6}

        # Estado
        top = ttk.Frame(f); top.pack(fill=tk.X, **pad)
        self.lbl_status = ttk.Label(top, text="Desconectado")
        self.lbl_status.pack(side=tk.LEFT)

        # ---- LOGIN ----
        login = ttk.LabelFrame(f, text="Login")
        login.pack(fill=tk.X, **pad)
        self.log_who = tk.StringVar(); self.log_pass = tk.StringVar()
        ttk.Label(login, text="Email o Usuario").grid(row=0, column=0, sticky="e", **pad)
        ttk.Entry(login, textvariable=self.log_who, width=32).grid(row=0, column=1, **pad)
        ttk.Label(login, text="Password").grid(row=0, column=2, sticky="e", **pad)
        ttk.Entry(login, textvariable=self.log_pass, show='*', width=24).grid(row=0, column=3, **pad)
        ttk.Button(login, text="Login", command=self._do_login).grid(row=0, column=4, **pad)

        # ---- REGISTRO ----
        reg = ttk.LabelFrame(f, text="Registro")
        reg.pack(fill=tk.X, **pad)
        self.reg_email = tk.StringVar(); self.reg_user = tk.StringVar(); self.reg_pw = tk.StringVar()
        ttk.Label(reg, text="Email").grid(row=0, column=0, sticky="e", **pad)
        ttk.Entry(reg, textvariable=self.reg_email, width=32).grid(row=0, column=1, **pad)
        ttk.Label(reg, text="Usuario").grid(row=0, column=2, sticky="e", **pad)
        ttk.Entry(reg, textvariable=self.reg_user, width=24).grid(row=0, column=3, **pad)
        ttk.Label(reg, text="Password").grid(row=0, column=4, sticky="e", **pad)
        ttk.Entry(reg, textvariable=self.reg_pw, show='*', width=24).grid(row=0, column=5, **pad)
        ttk.Button(reg, text="Registrar", command=self._do_register).grid(row=0, column=6, **pad)

        # ---- TOKENS ----
        toks = ttk.LabelFrame(f, text="Tokens JWT")
        toks.pack(fill=tk.BOTH, expand=False, **pad)
        ttk.Label(toks, text="Access token").grid(row=0, column=0, sticky='nw', **pad)
        self.txt_access = tk.Text(toks, height=4); self.txt_access.grid(row=0, column=1, columnspan=5, sticky='nwe', **pad)
        ttk.Label(toks, text="Refresh token").grid(row=1, column=0, sticky='nw', **pad)
        self.txt_refresh = tk.Text(toks, height=3); self.txt_refresh.grid(row=1, column=1, columnspan=5, sticky='nwe', **pad)
        ttk.Label(toks, text="Access exp (UTC)").grid(row=2, column=0, sticky='e', **pad)
        self.txt_exp = ttk.Entry(toks, width=40); self.txt_exp.grid(row=2, column=1, sticky='w', **pad)
        ttk.Button(toks, text="Refresh access token", command=self._do_refresh).grid(row=2, column=2, **pad)

        for i in range(6):
            toks.columnconfigure(i, weight=1)

    def _do_register(self):
        def worker():
            try:
                data = self.client.register(self.reg_email.get().strip(), self.reg_user.get().strip(), self.reg_pw.get())
                self.log("Registro ok.")
                self._update_status()
                messagebox.showinfo("Registro", "Usuario creado y autenticado.")
            except Exception as e:
                self.error(f"Registro: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _do_login(self):
        def worker():
            try:
                data = self.client.login(self.log_who.get().strip(), self.log_pass.get())
                self.log("Login ok.")
                self._update_status()
                messagebox.showinfo("Login", "Autenticado.")
            except Exception as e:
                self.error(f"Login: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _do_refresh(self):
        def worker():
            try:
                data = self.client.refresh()
                self.log("Access token renovado.")
                self._update_status()
            except Exception as e:
                self.error(f"Refresh: {e}")
        threading.Thread(target=worker, daemon=True).start()

    # ================= PROTECTED TAB =================
    def _build_protected_tab(self):
        f = self.tab_protected
        pad = {"padx": 8, "pady": 6}

        info = ttk.LabelFrame(f, text="/api/profile (requiere Authorization: Bearer <access_token>)")
        info.pack(fill=tk.BOTH, expand=True, **pad)

        top = ttk.Frame(info); top.pack(fill=tk.X, **pad)
        ttk.Button(top, text="Cargar Perfil", command=self._load_profile).pack(side=tk.LEFT)
        self.lbl_prot = ttk.Label(top, text="Estado: –")
        self.lbl_prot.pack(side=tk.LEFT, padx=10)

        self.txt_profile = tk.Text(info, height=18)
        self.txt_profile.pack(fill=tk.BOTH, expand=True, **pad)

    def _load_profile(self):
        def worker():
            try:
                self.lbl_prot.config(text="Estado: solicitando…")
                data = self.client.profile()
                self.txt_profile.delete("1.0", tk.END)
                self.txt_profile.insert(tk.END, json.dumps(data, indent=2, ensure_ascii=False))
                self.lbl_prot.config(text="Estado: 200 OK")
                self.log("Perfil cargado.")
            except Exception as e:
                self.lbl_prot.config(text="Estado: error")
                self.error(f"Perfil: {e}")
        threading.Thread(target=worker, daemon=True).start()

    # ================= BOOKS TAB =================
    def _build_books_tab(self):
        f = self.tab_books
        pad = {"padx": 8, "pady": 6}

        # Filtros y acciones
        filt = ttk.LabelFrame(f, text="Consulta")
        filt.pack(fill=tk.X, **pad)
        self.b_isbn = tk.StringVar(); self.b_author = tk.StringVar(); self.b_format = tk.StringVar()
        ttk.Button(filt, text="Todos", command=self._books_all).grid(row=0, column=0, **pad)
        ttk.Label(filt, text="ISBN").grid(row=0, column=1, sticky='e', **pad)
        ttk.Entry(filt, textvariable=self.b_isbn, width=18).grid(row=0, column=2, **pad)
        ttk.Button(filt, text="Buscar", command=self._books_by_isbn).grid(row=0, column=3, **pad)
        ttk.Label(filt, text="Autor").grid(row=0, column=4, sticky='e', **pad)
        ttk.Entry(filt, textvariable=self.b_author, width=22).grid(row=0, column=5, **pad)
        ttk.Button(filt, text="Buscar", command=self._books_by_author).grid(row=0, column=6, **pad)
        ttk.Label(filt, text="Formato").grid(row=0, column=7, sticky='e', **pad)
        ttk.Entry(filt, textvariable=self.b_format, width=16).grid(row=0, column=8, **pad)
        ttk.Button(filt, text="Buscar", command=self._books_by_format).grid(row=0, column=9, **pad)

        # Tabla
        self.tree_books = ttk.Treeview(f, columns=("isbn","titulo","autor","anio","genero","precio","stock","formato"), show='headings', height=14)
        for col, w in (
            ("isbn",130), ("titulo",240), ("autor",200), ("anio",60), ("genero",120), ("precio",80), ("stock",70), ("formato",90)
        ):
            self.tree_books.heading(col, text=col)
            self.tree_books.column(col, width=w, anchor=tk.W)
        self.tree_books.pack(fill=tk.BOTH, expand=True, **pad)

    # --- books helpers ---
    def _render_books_xml(self, xml_text: str):
        try:
            root = ET.fromstring(xml_text)
            if root.tag != 'catalog':
                self.error("Respuesta no es <catalog> (ver log)")
                self.log(xml_text)
                return
            rows = []
            for b in root.findall('book'):
                def tv(tag):
                    e = b.find(tag)
                    return e.text if e is not None else ''
                rows.append({
                    "isbn": b.attrib.get('isbn',''),
                    "titulo": tv('title'),
                    "autor": tv('author'),
                    "anio": tv('year'),
                    "genero": tv('genre'),
                    "precio": tv('price'),
                    "stock": tv('stock'),
                    "formato": tv('format'),
                })
            self.tree_books.delete(*self.tree_books.get_children())
            for r in rows:
                self.tree_books.insert('', tk.END, values=(r['isbn'], r['titulo'], r['autor'], r['anio'], r['genero'], r['precio'], r['stock'], r['formato']))
            self.log(f"Libros mostrados: {len(rows)}")
        except ET.ParseError as e:
            self.error(f"XML inválido: {e}")
            self.log(xml_text)

    def _books_all(self):
        def worker():
            try:
                xml = self.client.books_all()
                self._render_books_xml(xml)
            except Exception as e:
                self.error(f"Books all: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _books_by_isbn(self):
        def worker():
            try:
                q = self.b_isbn.get().strip()
                if not q:
                    messagebox.showwarning("Libros", "Escribe un ISBN")
                    return
                url = f"{self.client.books_base}/api/books/isbn/{q}"
                self._log(f"[books_by_isbn] GET {url}")
                resp = requests.get(url, timeout=10, headers={"Accept": "application/xml"})
                self._log(f"  => {resp.status_code} {resp.reason}")
                if resp.status_code >= 400:
                    self._log(f"  body={resp.text}")
                    self.error(f"Books by ISBN: {resp.status_code}")
                    return
                self._render_books_xml(resp.text)
            except Exception as e:
                self.error(f"Books by ISBN: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _books_by_author(self):
        def worker():
            try:
                q = self.b_author.get().strip()
                if not q:
                    messagebox.showwarning("Libros", "Escribe un autor")
                    return
                url = f"{self.client.books_base}/api/books/author/{q}"
                self._log(f"[books_by_author] GET {url}")
                resp = requests.get(url, timeout=10, headers={"Accept": "application/xml"})
                self._log(f"  => {resp.status_code} {resp.reason}")
                if resp.status_code >= 400:
                    self._log(f"  body={resp.text}")
                    self.error(f"Books by author: {resp.status_code}")
                    return
                self._render_books_xml(resp.text)
            except Exception as e:
                self.error(f"Books by author: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def _books_by_format(self):
        def worker():
            try:
                q = self.b_format.get().strip()
                if not q:
                    messagebox.showwarning("Libros", "Escribe un formato")
                    return
                url = f"{self.client.books_base}/api/books/format/{q}"
                self._log(f"[books_by_format] GET {url}")
                resp = requests.get(url, timeout=10, headers={"Accept": "application/xml"})
                self._log(f"  => {resp.status_code} {resp.reason}")
                if resp.status_code >= 400:
                    self._log(f"  body={resp.text}")
                    self.error(f"Books by format: {resp.status_code}")
                    return
                self._render_books_xml(resp.text)
            except Exception as e:
                self.error(f"Books by format: {e}")
        threading.Thread(target=worker, daemon=True).start()

if __name__ == "__main__":
    app = TkClient()
    app.mainloop()
