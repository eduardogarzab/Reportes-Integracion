# locustfile.py
import uuid, random
from locust import FastHttpUser, task, between, tag

# Si algún día montas detrás de un prefix (p.ej. /v1) ponlo aquí.
BASE_PATH = ""

def _rand_user():
    uid = uuid.uuid4().hex[:12]
    return (f"edu_{uid}@example.test", f"edu_{uid}", "Admin#2025")

class MicroserviceUser(FastHttpUser):
    """
    Pruebas de carga para el microservicio de Auth/Profile.
    - on_start: health -> register -> login (si hace falta)
    - flow_end_to_end: profile -> refresh -> introspect -> (logout opcional) -> login
    - tareas específicas por endpoint para mezcla de carga
    """
    # latencia artificial entre acciones (ajusta según tu escenario)
    wait_time = between(0.1, 0.8)

    def on_start(self):
        # Siempre define atributos para evitar AttributeError
        self.access = None
        self.refresh = None
        self.email, self.username, self.password = _rand_user()

        # Health (best-effort)
        self.client.get(f"{BASE_PATH}/health", name="GET /health", timeout=10, catch_response=False)

        # Register (esperado 201; tolera 409 por duplicado improbable)
        with self.client.post(
            f"{BASE_PATH}/auth/register",
            name="POST /auth/register",
            json={"email": self.email, "username": self.username, "password": self.password},
            timeout=10, catch_response=True
        ) as resp:
            if resp.status_code == 201:
                # tokens vienen dentro de "tokens" en register
                try:
                    toks = resp.json().get("tokens", {})
                    self.access = toks.get("access_token")
                    self.refresh = toks.get("refresh_token")
                    resp.success()
                except Exception as e:
                    resp.failure(f"bad register JSON: {e}")
            elif resp.status_code == 409:
                # Ya existía -> éxito lógico para la carga
                resp.success()
            else:
                resp.failure(f"register failed: {resp.status_code} {resp.text}")

        # Login si no tenemos tokens aún (p.ej. JSON raro o 409)
        if not self.access or not self.refresh:
            self._login()

    def on_stop(self):
        # Logout best-effort para “limpiar” sesiones
        if self.access:
            self.client.post(
                f"{BASE_PATH}/auth/logout",
                name="POST /auth/logout",
                headers=self._authz(),
                json={"refresh_token": self.refresh or ""},
                timeout=10, catch_response=False
            )

    # ---------------- helpers ----------------
    def _authz(self):
        return {"Authorization": f"Bearer {self.access}"} if self.access else {}

    def _login(self):
        with self.client.post(
            f"{BASE_PATH}/auth/login",
            name="POST /auth/login",
            json={"email": self.email, "password": self.password},
            timeout=10, catch_response=True
        ) as resp:
            if resp.status_code != 200:
                resp.failure(f"login failed: {resp.status_code} {resp.text}")
                self.access = None
                self.refresh = None
                return
            try:
                # En login también vienen dentro de "tokens"
                toks = resp.json().get("tokens", {})
                self.access = toks.get("access_token")
                self.refresh = toks.get("refresh_token")
                resp.success()
            except Exception as e:
                resp.failure(f"bad login JSON: {e}")
                self.access = None
                self.refresh = None

    # ---------------- flujo end-to-end (más peso) ----------------
    @tag("flow")
    @task(5)
    def flow_end_to_end(self):
        # Asegurar sesión
        if not self.access:
            self._login()
            if not self.access:
                return  # no insistas si no hay sesión

        # /api/profile protegido
        self.client.get(
            f"{BASE_PATH}/api/profile",
            name="GET /api/profile",
            headers=self._authz(),
            timeout=10, catch_response=False
        )

        # /auth/refresh (en tu servicio devuelve {access_token,...} a nivel raíz)
        if self.refresh:
            with self.client.post(
                f"{BASE_PATH}/auth/refresh",
                name="POST /auth/refresh",
                json={"refresh_token": self.refresh},
                timeout=10, catch_response=True
            ) as resp:
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        # Actualiza access (refresh NO regenera refresh en tu código)
                        self.access = data.get("access_token", self.access)
                        resp.success()
                    except Exception as e:
                        resp.failure(f"bad refresh JSON: {e}")
                else:
                    resp.failure(f"refresh failed: {resp.status_code} {resp.text}")

        # /auth/introspect (con el access)
        if self.access:
            self.client.post(
                f"{BASE_PATH}/auth/introspect",
                name="POST /auth/introspect",
                json={"token": self.access},
                timeout=10, catch_response=False
            )

        # churn ~15%: logout y login para simular rotación de sesión
        if random.random() < 0.15 and self.access:
            self.client.post(
                f"{BASE_PATH}/auth/logout",
                name="POST /auth/logout",
                headers=self._authz(),
                json={"refresh_token": self.refresh or ""},
                timeout=10, catch_response=False
            )
            self._login()

    # ---------------- tareas por endpoint (carga mixta) ----------------
    @tag("health")
    @task(1)
    def t_health(self):
        self.client.get(f"{BASE_PATH}/health", name="GET /health", timeout=10, catch_response=False)

    @tag("register")
    @task(1)
    def t_register(self):
        # registro “stateless” (no toca self.access)
        email, username, password = _rand_user()
        self.client.post(
            f"{BASE_PATH}/auth/register",
            name="POST /auth/register [stateless]",
            json={"email": email, "username": username, "password": password},
            timeout=10, catch_response=False
        )

    @tag("login")
    @task(2)
    def t_login(self):
        # login “stateless” (no toca self.access)
        self.client.post(
            f"{BASE_PATH}/auth/login",
            name="POST /auth/login [stateless]",
            json={"email": self.email, "password": self.password},
            timeout=10, catch_response=False
        )

    @tag("profile")
    @task(3)
    def t_profile(self):
        if self.access:
            self.client.get(
                f"{BASE_PATH}/api/profile",
                name="GET /api/profile [stateless]",
                headers=self._authz(),
                timeout=10, catch_response=False
            )

    @tag("refresh")
    @task(2)
    def t_refresh(self):
        if self.refresh:
            self.client.post(
                f"{BASE_PATH}/auth/refresh",
                name="POST /auth/refresh [stateless]",
                json={"refresh_token": self.refresh},
                timeout=10, catch_response=False
            )

    @tag("introspect")
    @task(1)
    def t_introspect(self):
        if self.access:
            self.client.post(
                f"{BASE_PATH}/auth/introspect",
                name="POST /auth/introspect [access]",
                json={"token": self.access},
                timeout=10, catch_response=False
            )

    @tag("logout")
    @task(1)
    def t_logout(self):
        if self.access:
            self.client.post(
                f"{BASE_PATH}/auth/logout",
                name="POST /auth/logout [stateless]",
                headers=self._authz(),
                json={"refresh_token": self.refresh or ""},
                timeout=10, catch_response=False
            )
