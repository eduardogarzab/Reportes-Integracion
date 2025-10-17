import csv
from faker import Faker

# Inicializa Faker para generar datos falsos
fake = Faker()

# Nombre del archivo de salida
output_file = 'users.csv'
num_users = 300

print(f"Generando {num_users} usuarios en {output_file}...")

with open(output_file, 'w', newline='') as csvfile:
    # Define los encabezados del CSV
    fieldnames = ['email', 'password', 'username']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()

    for i in range(num_users):
        email = fake.unique.email()
        password = fake.password(length=12)
        # Genera un nombre de usuario único para evitar colisiones
        username = fake.unique.user_name() + str(fake.random_int(min=1, max=999))

        writer.writerow({'email': email, 'password': password, 'username': username})

print("¡Archivo users.csv generado con éxito!")
