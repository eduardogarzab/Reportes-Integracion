import csv
import itertools
import random
import uuid
from locust import HttpUser, task, between, LoadTestShape
import time

# --- CONFIGURACIÓN ---
# URLs de tus servicios en GCP
AUTH_SERVICE_URL = "http://35.225.153.19:5000"
BOOKS_SERVICE_URL = "http://35.225.153.19:5001"

# --- CSV FEEDER ---
# Lee los datos de usuario del archivo users.csv
try:
    with open('users.csv', 'r') as f:
        # Usamos itertools.cycle para que la lista de usuarios se repita si se acaba
        user_credentials = itertools.cycle(list(csv.DictReader(f)))
except FileNotFoundError:
    print("Error: El archivo 'users.csv' no fue encontrado. Por favor, genéralo primero.")
    exit()

class AuthenticatedUser(HttpUser):
    """
    Clase base que maneja la autenticación para cada usuario virtual.
    Inicia sesión una vez y guarda el token de acceso.
    """
    abstract = True
    token = None

    def on_start(self):
        """Esta función se ejecuta una vez por cada usuario simulado al iniciar."""
        self.login()

    def login(self):
        """Obtiene credenciales del CSV y realiza el login enviando el username."""
        credentials = next(user_credentials)
        try:
            response = self.client.post(f"{AUTH_SERVICE_URL}/login", json={
                "username": credentials['username'], # <-- Corregido para usar username
                "password": credentials['password']
            }, name="/login")

            if response.status_code == 200:
                self.token = response.json().get('access_token')
            else:
                print(f"Fallo en login para {credentials.get('username', 'N/A')}: {response.status_code} {response.text}")
                self.token = None
        except Exception as e:
            print(f"Excepción durante el login: {e}")
            self.token = None

    def get_auth_headers(self):
        """Devuelve los encabezados de autorización necesarios para las peticiones."""
        if not self.token:
            return {}
        return {'Authorization': f'Bearer {self.token}'}


class BookstoreUser(AuthenticatedUser):
    """
    Define las tareas que un usuario realizará en el microservicio de libros.
    Hereda la lógica de login de AuthenticatedUser.
    """
    host = BOOKS_SERVICE_URL
    wait_time = between(1, 5) # Tiempo de espera aleatorio entre tareas

    # === TAREAS DE LECTURA (Mayor prioridad para simular Read-Heavy) ===
    @task(10) # Se ejecutará 10 veces más que las tareas con peso 1
    def get_all_books(self):
        self.client.get("/api/books", headers=self.get_auth_headers(), name="/api/books [GET]")

    @task(5)
    def get_book_by_isbn(self):
        # Usamos ISBNs que sabemos que existen en la BBDD
        isbns = ["978-0061120084", "978-0140449136", "978-0553380163"]
        isbn = random.choice(isbns)
        self.client.get(f"/api/books/isbn/{isbn}", headers=self.get_auth_headers(), name="/api/books/isbn/[isbn] [GET]")

    @task(3)
    def get_books_by_author(self):
        authors = ["George Orwell", "Homer", "Jane Austen"]
        author = random.choice(authors)
        self.client.get(f"/api/books/author/{author}", headers=self.get_auth_headers(), name="/api/books/author/[author] [GET]")

    # === TAREA DE ESCRITURA (Menor prioridad) ===
    @task(1)
    def insert_book(self):
        # Datos válidos para una inserción exitosa
        genres = ["Fiction", "Epic", "Romance", "Dystopian"]
        formats = ["Físico", "Digital"]
        authors = ["George Orwell", "Jane Austen"]

        payload = {
            "isbn": f"TEST-{int(time.time())}-{random.randint(1000, 9999)}", # ISBN único para evitar conflictos de duplicados
            "title": f"New Test Book {random.randint(1000, 9999)}",
            "year": random.randint(1990, 2025),
            "price": round(random.uniform(9.99, 49.99), 2),
            "stock": random.randint(1, 100),
            "genre": random.choice(genres),
            "format": random.choice(formats),
            "authors": random.choice(authors)
        }
        self.client.post("/api/books/insert", json=payload, headers=self.get_auth_headers(), name="/api/books/insert [POST]")


class StagesShape(LoadTestShape):
    """
    Clase para controlar la forma de la carga (rampas, picos, valles).
    Usada para las pruebas de Ramp-up, Spike y Ramp-down.
    """
    stages = [
        {"duration": 60, "users": 100, "spawn_rate": 10},      # Ramp-up a 100 usuarios en 1 min
        {"duration": 180, "users": 100, "spawn_rate": 10},     # Carga estable por 2 mins
        {"duration": 190, "users": 500, "spawn_rate": 100},    # Spike: sube 400 usuarios en 10 seg
        {"duration": 240, "users": 500, "spawn_rate": 50},     # Sostiene el pico por ~1 min
        {"duration": 300, "users": 50, "spawn_rate": 50},      # Ramp-down a 50 usuarios
        {"duration": 360, "users": 50, "spawn_rate": 10},      # Carga ligera final
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        return None # Finaliza la prueba
