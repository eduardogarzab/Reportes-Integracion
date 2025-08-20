## Pasos y comandos utilizados

# 1. Instalar plugins de DNF necesarios para manejar repositorios
sudo dnf -y install dnf-plugins-core

# 2. Agregar el repositorio oficial de Docker para RHEL
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

# 3. Instalar Docker CE, su CLI y containerd
sudo dnf install -y docker-ce docker-ce-cli containerd.io

# 4. Habilitar y arrancar el servicio de Docker, y verificar su estado
sudo systemctl enable --now docker
sudo systemctl status docker

# 5. Ejecutar el contenedor de Ollama en segundo plano, exponiendo el puerto 11434
sudo docker run -d -p 11434:11434 --name ollama ollama/ollama

# 6. Descargar el modelo gemma3:1b dentro del contenedor
sudo docker exec -it ollama ollama pull gemma3:1b

# 7. Verificar qué modelos están disponibles en el contenedor
sudo docker exec -it ollama ollama list

# 8. Probar el modelo ejecutándolo directamente desde el contenedor
sudo docker exec -it ollama ollama run gemma3:1b

# 9. Probar el API de Ollama con el endpoint /api/chat, enviando un mensaje al modelo gemma3:1b
curl http://localhost:11434/api/chat -d "{
  \"model\": \"gemma3:1b\",
  \"messages\":[{\"role\":\"user\",\"content\":\"¿Qué es Ollama?\"}]
}"
