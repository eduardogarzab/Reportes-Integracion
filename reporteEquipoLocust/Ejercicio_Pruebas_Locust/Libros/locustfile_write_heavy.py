import csv
import itertools
import random
import uuid
import time
from locust import HttpUser, task, between

# --- CONFIGURACIÓN ---
# Las URLs son las mismas que en el otro archivo
AUTH_SERVICE_URL = "http://35.225.153.19:5000"
BOOKS_SERVICE_URL = "http://35.225.153.19:5001"

# --- CSV FEEDER ---
try:
    with open('users.csv', 'r') as f:
        user_credentials = itertools.cycle(list(csv.DictReader(f)))
except FileNotFoundError:
    print("Error: El archivo 'users.csv' no fue encontrado.")
    exit()

class AuthenticatedUser(HttpUser):
    abstract = True
    token = None

    def on_start(self):
        self.login()

    def login(self):
        credentials = next(user_credentials)
        try:
            response = self.client.post(f"{AUTH_SERVICE_URL}/login", json={
                "username": credentials['username'],
                "password": credentials['password']
            }, name="/login")
            if response.status_code == 200:
                self.token = response.json().get('access_token')
            else:
                self.token = None
        except Exception:
            self.token = None

    def get_auth_headers(self):
        return {'Authorization': f'Bearer {self.token}'} if self.token else {}

class WriteHeavyBookstoreUser(AuthenticatedUser):
    host = BOOKS_SERVICE_URL
    wait_time = between(1, 5)

    # =================================================================
    # === AJUSTE PRINCIPAL AQUÍ (PESOS INVERTIDOS) ===
    # =================================================================

    # === TAREAS DE LECTURA (Baja prioridad) ===
    @task(1) # <-- Peso bajo
    def get_all_books(self):
        self.client.get("/api/books", headers=self.get_auth_headers(), name="/api/books [GET]")

    @task(1) # <-- Peso bajo
    def get_book_by_isbn(self):
        isbns = ["978-0061120084", "978-0140449136", "978-0553380163"]
        self.client.get(f"/api/books/isbn/{random.choice(isbns)}", headers=self.get_auth_headers(), name="/api/books/isbn/[isbn] [GET]")

    # === TAREA DE ESCRITURA (Alta prioridad) ===
    @task(10) # <-- Peso alto
    def insert_book(self):
        payload = {
            "isbn": f"TEST-{int(time.time())}-{random.randint(1000, 9999)}",
            "title": f"Write Heavy Test Book {random.randint(1000, 9999)}",
            "year": 2025,
            "price": 25.50,
            "stock": 50,
            "genre": "Fiction",
            "format": "Digital",
            "authors": "George Orwell"
        }
        self.client.post("/api/books/insert", json=payload, headers=self.get_auth_headers(), name="/api/books/insert [POST]")
