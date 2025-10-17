"""Locust scenarios for HeartGuard superadmin CMS."""
from __future__ import annotations

import os
import queue
import random
import re
from pathlib import Path
from typing import Optional

import gevent

from locust import HttpUser, LoadTestShape, TaskSet, between, events
from locust.exception import StopUser

USERS_CSV = Path(__file__).resolve().parent / "data" / "users.csv"
CREDENTIAL_POOL: queue.Queue[tuple[str, str]] = queue.Queue()
LOGIN_CSRF_RE = re.compile(
    r"<input[^>]*name=['\"]_csrf['\"][^>]*value=['\"]([^'\"]+)['\"]",
    re.IGNORECASE,
)
STATUS_FORM_RE = re.compile(r'action="/superadmin/users/([0-9a-f\-]+)/status"')
STATUS_SELECTED_RE = re.compile(r'<option value="([a-z_]+)"[^>]*selected', re.IGNORECASE)
ROLE_FORM_RE = re.compile(r'action="/superadmin/roles/users/([0-9a-f\-]+)"')
ROLE_SELECTED_RE = re.compile(r'<option value="([0-9a-f\-]+)"[^>]*selected', re.IGNORECASE)

READ_ENDPOINTS = [
    "/superadmin/dashboard",
    "/superadmin/users",
    "/superadmin/organizations",
    "/superadmin/content",
    "/superadmin/patients",
    "/superadmin/alerts",
    "/superadmin/audit",
    "/superadmin/settings/system",
]


def _load_credentials() -> None:
    if CREDENTIAL_POOL.qsize() > 0:
        return
    if not USERS_CSV.exists():
        raise FileNotFoundError(f"users.csv not found at {USERS_CSV}")
    with USERS_CSV.open(newline="", encoding="utf-8") as handle:
        next(handle)  # skip header
        for line in handle:
            email, password = line.strip().split(",", maxsplit=1)
            if email and password:
                CREDENTIAL_POOL.put((email, password))
    if CREDENTIAL_POOL.qsize() == 0:
        raise ValueError("users.csv did not provide any credentials")


@events.test_start.add_listener
def _on_test_start(environment, **_kwargs):  # noqa: D401, ANN001
    _load_credentials()


class HeartGuardUser(HttpUser):
    """Base user handling authentication and shared helpers."""

    abstract = True
    wait_time = between(1, 3)

    def __init__(self, environment):  # noqa: D401
        super().__init__(environment)
        self.credential: Optional[tuple[str, str]] = None
        self.session_csrf: Optional[str] = None
        self.primary_user_id: Optional[str] = None
        self.primary_user_status: Optional[str] = None
        self.primary_role_id: Optional[str] = None
        default_host = os.getenv("HEARTGUARD_BASE_URL")
        if default_host:
            self.host = default_host

    def on_start(self) -> None:  # noqa: D401
        try:
            self.credential = CREDENTIAL_POOL.get_nowait()
        except queue.Empty as exc:
            raise StopUser("No credentials left in queue") from exc
        self.login()

    def on_stop(self) -> None:  # noqa: D401
        if self.credential is not None:
            CREDENTIAL_POOL.put(self.credential)
            self.credential = None

    # --- login helpers -------------------------------------------------

    def login(self) -> None:
        email, password = self.credential or ("", "")
        token = self._fetch_login_csrf()
        payload = {"email": email, "password": password, "_csrf": token}
        login_response = self.client.post(
            "/login",
            data=payload,
            name="POST /login",
            allow_redirects=False,
        )
        if login_response.status_code in (302, 303):
            location = login_response.headers.get("Location", "/superadmin/dashboard")
            self.client.get(location, name=f"GET {location}")
        elif login_response.status_code >= 400:
            raise StopUser(f"Login failed for {email}: {login_response.status_code}")
        self.refresh_session_state()

    def refresh_session_state(self) -> None:
        response = self.client.get("/superadmin/users", name="GET /superadmin/users")
        csrf = self._extract_csrf(response.text)
        if csrf:
            self.session_csrf = csrf
        self._extract_user_targets(response.text)

    def _fetch_login_csrf(self, max_attempts: int = 3) -> str:
        last_response = None
        for attempt in range(max_attempts):
            response = self.client.get("/login", name="GET /login")
            last_response = response
            token = self._extract_csrf(response.text)
            if token:
                return token
            if response.status_code in (429, 503):
                gevent.sleep(1 + attempt)
                continue
            if response.status_code >= 400:
                raise StopUser(
                    f"Login form returned {response.status_code} while fetching CSRF token",
                )
            gevent.sleep(0.5 + attempt * 0.5)
        body_preview = ""
        if last_response is not None:
            snippet = last_response.text.strip()
            body_preview = snippet[:200].replace("\n", " ")
        raise StopUser(
            "Could not locate CSRF token on login form after retries"
            + (f" (status {last_response.status_code}; body: {body_preview!r})" if last_response else ""),
        )

    @staticmethod
    def _extract_csrf(html: str) -> Optional[str]:
        match = LOGIN_CSRF_RE.search(html)
        if match:
            return match.group(1)
        return None

    def _extract_user_targets(self, html: str) -> None:
        status_match = STATUS_FORM_RE.search(html)
        if status_match:
            self.primary_user_id = status_match.group(1)
            snippet = html[status_match.start() : status_match.end() + 400]
            selected = STATUS_SELECTED_RE.search(snippet)
            if selected:
                self.primary_user_status = selected.group(1)
        role_match = ROLE_FORM_RE.search(html)
        if role_match:
            target_id = role_match.group(1)
            if not self.primary_user_id:
                self.primary_user_id = target_id
            snippet = html[role_match.start() : role_match.end() + 400]
            selected_role = ROLE_SELECTED_RE.search(snippet)
            if selected_role:
                self.primary_role_id = selected_role.group(1)

    # --- task helpers --------------------------------------------------

    def view_dashboard(self) -> None:
        self.client.get("/superadmin/dashboard", name="GET /superadmin/dashboard")

    def view_random_page(self) -> None:
        target = random.choice(READ_ENDPOINTS)
        self.client.get(target, name=f"GET {target}")

    def export_dashboard_csv(self) -> None:
        self.client.get(
            "/superadmin/dashboard/export?format=csv",
            name="GET /superadmin/dashboard/export?format=csv",
        )

    def maintain_user_status(self) -> None:
        if not self.session_csrf or not self.primary_user_id or not self.primary_user_status:
            self.refresh_session_state()
            return
        payload = {
            "_csrf": self.session_csrf,
            "status": self.primary_user_status,
            "redirect": "/superadmin/users",
        }
        self.client.post(
            f"/superadmin/users/{self.primary_user_id}/status",
            data=payload,
            name="POST /superadmin/users/:id/status",
            allow_redirects=False,
        )

    def reapply_role_assignment(self) -> None:
        if not self.session_csrf or not self.primary_user_id or not self.primary_role_id:
            self.refresh_session_state()
            return
        payload = {
            "_csrf": self.session_csrf,
            "role_id": self.primary_role_id,
            "redirect": "/superadmin/users",
        }
        self.client.post(
            f"/superadmin/roles/users/{self.primary_user_id}",
            data=payload,
            name="POST /superadmin/roles/users/:id",
            allow_redirects=False,
        )


class BaselineTasks(TaskSet):
    def on_start(self):
        if not isinstance(self.user, HeartGuardUser):
            raise StopUser("baseline taskset only works with HeartGuardUser")

    @events.quitting.add_listener
    def _cleanup(environment, **_kwargs):  # noqa: D401, ANN001
        while not CREDENTIAL_POOL.empty():
            try:
                CREDENTIAL_POOL.get_nowait()
            except queue.Empty:
                break

    def view_random_page_task(self):
        self.user.view_random_page()

    def maintain_user_status_task(self):
        self.user.maintain_user_status()

    def view_dashboard_task(self):
        self.user.view_dashboard()

    def export_dashboard_csv_task(self):
        self.user.export_dashboard_csv()

    tasks = {
        view_random_page_task: 5,
        view_dashboard_task: 3,
        export_dashboard_csv_task: 1,
        maintain_user_status_task: 1,
    }


class ReadHeavyTasks(TaskSet):
    def view_random_page_task(self):
        self.user.view_random_page()

    def view_dashboard_task(self):
        self.user.view_dashboard()

    def export_dashboard_csv_task(self):
        self.user.export_dashboard_csv()

    def maintain_user_status_task(self):
        self.user.maintain_user_status()

    tasks = {
        view_random_page_task: 8,
        view_dashboard_task: 4,
        export_dashboard_csv_task: 1,
        maintain_user_status_task: 1,
    }


class WriteHeavyTasks(TaskSet):
    def maintain_user_status_task(self):
        self.user.maintain_user_status()

    def reapply_role_assignment_task(self):
        self.user.reapply_role_assignment()

    def view_random_page_task(self):
        self.user.view_random_page()

    def export_dashboard_csv_task(self):
        self.user.export_dashboard_csv()

    tasks = {
        maintain_user_status_task: 4,
        reapply_role_assignment_task: 3,
        view_random_page_task: 2,
        export_dashboard_csv_task: 1,
    }


class SmokeTasks(TaskSet):
    def view_dashboard_task(self):
        self.user.view_dashboard()

    def view_random_page_task(self):
        self.user.view_random_page()

    tasks = {
        view_dashboard_task: 2,
        view_random_page_task: 1,
    }


class BaselineUser(HeartGuardUser):
    tasks = [BaselineTasks]


class SmokeUser(HeartGuardUser):
    wait_time = between(2, 4)
    tasks = [SmokeTasks]


class ReadHeavyUser(HeartGuardUser):
    tasks = [ReadHeavyTasks]


class WriteHeavyUser(HeartGuardUser):
    tasks = [WriteHeavyTasks]


# --- Load test shapes -------------------------------------------------


def _stage_shape(name: str, stages: tuple[tuple[int, int, int], ...]) -> type[LoadTestShape]:
    class StageShape(LoadTestShape):
        _stages = stages

        def tick(self):  # noqa: D401
            run_time = self.get_run_time()
            elapsed = 0
            for duration, users, spawn in self._stages:
                elapsed += duration
                if run_time <= elapsed:
                    return users, spawn
            return None

    StageShape.__name__ = name
    return StageShape


def _breakpoint_shape() -> type[LoadTestShape]:
    class BreakpointShape(LoadTestShape):
        step_duration = 60
        max_users = 500
        increment = 40

        def tick(self):  # noqa: D401
            run_time = self.get_run_time()
            step = int(run_time // self.step_duration)
            users = min((step + 1) * self.increment, self.max_users)
            if users <= 0:
                users = self.increment
            return users, self.increment

    return BreakpointShape


SHAPE_FACTORIES = {
    "baseline": lambda: _stage_shape("BaselineShape", ((60, 25, 5), (600, 25, 5))),
    "ramp": lambda: _stage_shape(
        "RampUpDownShape",
        (
            (60, 20, 4),
            (180, 60, 6),
            (300, 120, 10),
            (420, 60, 6),
            (540, 20, 4),
            (600, 0, 1),
        ),
    ),
    "spike": lambda: _stage_shape(
        "SpikeShape",
        (
            (30, 15, 5),
            (90, 150, 50),
            (150, 15, 5),
            (210, 0, 1),
        ),
    ),
    "soak": lambda: _stage_shape("SoakShape", ((60 * 30, 40, 2),)),
    "breakpoint": _breakpoint_shape,
}


_shape_name = os.getenv("HEARTGUARD_SHAPE", "").strip().lower()
if _shape_name:
    factory = SHAPE_FACTORIES.get(_shape_name)
    if factory is None:
        available = ", ".join(sorted(SHAPE_FACTORIES))
        raise RuntimeError(f"Unknown HEARTGUARD_SHAPE '{_shape_name}'. Choose one of: {available}")
    shape_class = factory()
