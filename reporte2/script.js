const chatContainer = document.getElementById("chatContainer");
const messageInput = document.getElementById("messageInput");
const sendButton = document.getElementById("sendButton");
const buttonText = document.getElementById("buttonText");
const typingIndicator = document.getElementById("typingIndicator");

const OLLAMA_API_URL = "http://localhost:11434/api/chat";
const MODEL_NAME = "gemma3:1b";

function addMessage(content, isUser = false) {
	const messageDiv = document.createElement("div");
	messageDiv.className = `message ${isUser ? "user" : "bot"}`;
	const avatar = document.createElement("div");
	avatar.className = "message-avatar";
	avatar.textContent = isUser ? "👤" : "🤖";
	const messageContent = document.createElement("div");
	messageContent.className = "message-content";
	messageContent.textContent = content;
	messageDiv.appendChild(avatar);
	messageDiv.appendChild(messageContent);
	chatContainer.appendChild(messageDiv);
	chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTypingIndicator(show) {
	typingIndicator.style.display = show ? "block" : "none";
	if (show) chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function sendMessage() {
	const message = messageInput.value.trim();
	if (!message) return;

	sendButton.disabled = true;
	buttonText.innerHTML = '<div class="loading"></div>';
	messageInput.disabled = true;

	addMessage(message, true);
	messageInput.value = "";
	showTypingIndicator(true);

	try {
		const requestData = {
			model: MODEL_NAME,
			messages: [{ role: "user", content: message }],
			stream: false,
		};

		const response = await fetch(OLLAMA_API_URL, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(requestData),
		});

		if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
		const data = await response.json();

		showTypingIndicator(false);

		if (data.message && data.message.content) {
			addMessage(data.message.content, false);
		} else {
			addMessage("Lo siento, no pude procesar tu mensaje.", false);
		}
	} catch (error) {
		console.error("Error:", error);
		showTypingIndicator(false);
		addMessage(`Error de conexión: ${error.message}`, false);
	} finally {
		sendButton.disabled = false;
		buttonText.textContent = "Enviar";
		messageInput.disabled = false;
		messageInput.focus();
	}
}

messageInput.addEventListener("keypress", function (e) {
	if (e.key === "Enter" && !e.shiftKey) {
		e.preventDefault();
		sendMessage();
	}
});

window.addEventListener("load", function () {
	messageInput.focus();
});
