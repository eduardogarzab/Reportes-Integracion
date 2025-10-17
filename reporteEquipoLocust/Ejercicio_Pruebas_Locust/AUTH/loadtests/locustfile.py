import csv
import queue
from locust import HttpUser, task, between, LoadTestShape

# --- CSV Feeder ---
# Usamos un patrón Singleton para asegurar que el archivo CSV se lea solo una vez.
class CSVReader:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CSVReader, cls).__new__(cls)
            cls._instance._init_data(*args, **kwargs)
        return cls._instance

    def _init_data(self, file_path):
        self.data_queue = queue.Queue()
        try:
            with open(file_path, 'r') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    self.data_queue.put(row)
        except FileNotFoundError:
            print(f"Error: El archivo {file_path} no se encuentra. Asegúrate de que 'users.csv' esté en el mismo directorio.")
            exit(1)

    def get_user_data(self):
        try:
            # Obtiene un usuario de la cola
            return self.data_queue.get_nowait()
        except queue.Empty:
            print("Advertencia: No hay más datos de usuarios en el CSV. Los usuarios de Locust se reutilizarán.")
            return None

# Inicializa el lector con tu archivo CSV
csv_reader = CSVReader('users.csv')


# --- Comportamiento del Usuario ---
class AuthenticatedUser(HttpUser):
    wait_time = between(1, 3)  # Tiempo de espera entre tareas (1-3 segundos)

    def on_start(self):
        """Se ejecuta cuando un usuario virtual de Locust inicia."""
        self.access_token = None
        self.refresh_token = None

        # Obtiene credenciales del CSV
        user_credentials = csv_reader.get_user_data()
        if user_credentials:
            self.username = user_credentials['username']
            self.email = user_credentials['email']
            self.password = user_credentials['password']
            self.login()
        else:
            # Si no hay más usuarios en el CSV, detiene a este usuario virtual.
            self.stop()

    def login(self):
        """Autentica al usuario y guarda los tokens."""
        response = self.client.post("/auth/login", json={
            "identifier": self.email,
            "password": self.password
        })
        if response.status_code == 200:
            tokens = response.json().get("tokens", {})
            self.access_token = tokens.get("access")
            self.refresh_token = tokens.get("refresh")

    # --- Escenarios de Prueba (Tasks) ---

    @task(5) # Read-heavy: Esta tarea se ejecutará 5 veces más que las otras.
    def get_user_profile(self):
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.client.get("/api/user-profile", headers=headers, name="/api/user-profile")

    @task(1) # Write-heavy (en este caso, solo refrescar, podrías añadir más POST/PUT)
    def refresh_token(self):
        if self.refresh_token:
            headers = {"Authorization": f"Bearer {self.refresh_token}"}
            response = self.client.post("/auth/refresh", headers=headers, name="/auth/refresh")
            if response.status_code == 200:
                self.access_token = response.json().get("access")


# --- Clase para Pruebas de Carga con Forma (Ramp-up, Spike, etc.) ---
class RampAndSpikeShape(LoadTestShape):
    """
    Define una forma de carga personalizada:
    - 1 minuto: Rampa de 0 a 150 usuarios.
    - 2 minutos: Carga estable de 150 usuarios.
    - 1 minuto: Rampa de 150 a 300 usuarios.
    - 3 minutos: Carga estable de 300 usuarios.
    - 1 minuto: Rampa de 300 a 1000 usuarios (Spike Test).
    - 30 segundos: Carga máxima de 1000 usuarios.
    - 1 minuto: Rampa de bajada de 1000 a 0 usuarios.
    """
    stages = [
        {"duration": 60, "users": 150, "spawn_rate": 50},
        {"duration": 180, "users": 150, "spawn_rate": 50},
        {"duration": 240, "users": 300, "spawn_rate": 50},
        {"duration": 420, "users": 300, "spawn_rate": 50},
        {"duration": 430, "users": 1000, "spawn_rate": 500}, # Spike
        {"duration": 460, "users": 1000, "spawn_rate": 500},
        {"duration": 520, "users": 0, "spawn_rate": 100},
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data
        return None # Fin de la prueba