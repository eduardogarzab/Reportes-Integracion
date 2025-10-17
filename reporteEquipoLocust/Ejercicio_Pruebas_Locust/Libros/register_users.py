import csv
import requests
import time

# --- CONFIGURACIÓN ---
# ¡IMPORTANTE! Ajusta esta URL a la de tu servicio de autenticación
AUTH_SERVICE_URL = "http://35.225.153.19:5000"
REGISTER_ENDPOINT = f"{AUTH_SERVICE_URL}/register"
CSV_FILE = 'users.csv'

def register_users():
    """Lee el archivo CSV y registra cada usuario vía API."""
    try:
        with open(CSV_FILE, mode='r') as infile:
            reader = csv.DictReader(infile)
            print(f"Iniciando registro de usuarios desde {CSV_FILE} en {REGISTER_ENDPOINT}...")
            
            for row in reader:
                payload = {
                    "username": row['username'],
                    "email": row['email'],
                    "password": row['password']
                }
                
                try:
                    # Realiza la petición POST para registrar al usuario
                    response = requests.post(REGISTER_ENDPOINT, json=payload)
                    
                    if response.status_code == 201:
                        print(f"✅ Usuario {row['email']} registrado con éxito.")
                    else:
                        # Imprime el error si el registro falla
                        print(f"❌ Error al registrar a {row['email']}. Status: {response.status_code}, Body: {response.text}")
                
                except requests.exceptions.RequestException as e:
                    print(f"🚨 Error de conexión al intentar registrar a {row['email']}: {e}")
                    # Si el servicio no está disponible, no tiene sentido continuar
                    break
                
                # Pequeña pausa para no saturar el servicio de registro
                time.sleep(0.1)

    except FileNotFoundError:
        print(f"Error: No se encontró el archivo '{CSV_FILE}'. Asegúrate de generarlo primero.")

if __name__ == "__main__":
    register_users()
