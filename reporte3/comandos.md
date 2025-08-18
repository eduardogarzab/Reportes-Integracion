sudo dnf -y install dnf-plugins-core

sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo

sudo dnf install -y docker-ce docker-ce-cli containerd.io

sudo systemctl enable --now docker
sudo systemctl status docker

sudo docker run -d -p 11434:11434 --name ollama ollama/ollama

sudo docker exec -it ollama ollama pull gemma3:1b

sudo docker exec -it ollama ollama list

sudo docker exec -it ollama ollama run gemma3:1b

curl http://localhost:11434/api/chat -d "{
  \"model\": \"gemma3:1b\",
  \"messages\":[{\"role\":\"user\",\"content\":\"¿Qué es Ollama?\"}]
}"

