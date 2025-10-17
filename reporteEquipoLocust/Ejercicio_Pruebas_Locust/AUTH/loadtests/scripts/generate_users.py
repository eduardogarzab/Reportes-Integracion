import csv
from faker import Faker

# Inicializa Faker para generar datos
fake = Faker()

# Número de usuarios a generar
num_users = 300

# Nombre del archivo de salida
file_name = 'users.csv'

# Abre el archivo en modo escritura
with open(file_name, 'w', newline='') as csvfile:
    # Define los nombres de las columnas
    fieldnames = ['username', 'email', 'password']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    # Escribe la cabecera
    writer.writeheader()

    # Genera y escribe los datos de cada usuario
    for _ in range(num_users):
        username = fake.user_name()
        email = fake.email()
        password = fake.password(length=12)
        writer.writerow({'username': username, 'email': email, 'password': password})

print(f"✅ Se ha generado el archivo '{file_name}' con {num_users} usuarios.")