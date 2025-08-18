# Reporte de Ejercicio Práctico

## Pasos y comandos utilizados

# 1. Ejecutar el contenedor de Ollama en segundo plano
docker run -d -p 11434:11434 --name ollama ollama/ollama

# 2. Descargar el modelo gemma3:1b dentro del contenedor
docker exec -it ollama ollama pull gemma3:1b

# 3. Verificar qué modelos están disponibles en el contenedor
docker exec -it ollama ollama list

# 4. Probar el modelo ejecutándolo directamente
docker exec -it ollama ollama run gemma3:1b

# 5. Prueba del API de Ollama con endpoint /api/chat
curl http://localhost:11434/api/chat -d "{
  \"model\": \"gemma3:1b\",
  \"messages\":[{\"role\":\"user\",\"content\":\"¿Qué es Ollama?\"}]
}"