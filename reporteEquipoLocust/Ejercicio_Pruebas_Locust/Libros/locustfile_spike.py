# Importa las clases necesarias del archivo principal
from locustfile import BookstoreUser, LoadTestShape

class SpikeTestShape(LoadTestShape):
    """
    Define una carga que simula un pico de tráfico repentino.
    """
    stages = [
        {"duration": 60, "users": 50, "spawn_rate": 10},      # 1. Baseline por 1 min
        {"duration": 70, "users": 1000, "spawn_rate": 95},    # 2. Spike: +950 usuarios en 10 seg
        {"duration": 130, "users": 1000, "spawn_rate": 50},   # 3. Hold: Mantener pico por 1 min
        {"duration": 150, "users": 0, "spawn_rate": 50},      # 4. Ramp-down a 0
    ]

    def tick(self):
        run_time = self.get_run_time()
        for stage in self.stages:
            if run_time < stage["duration"]:
                return (stage["users"], stage["spawn_rate"])
        return None
