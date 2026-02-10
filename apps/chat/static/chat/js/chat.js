let currentChatUserId = null;

function openChatModal(user) {
  currentChatUserId = user.id;

  document.getElementById("chatAvatar").src = user.avatar;
  document.getElementById("chatName").innerText = user.name;
  document.getElementById("chatRole").innerText = user.role;

  document.getElementById("chatMessages").innerHTML = "";
  document.getElementById("chatModal").classList.remove("hidden");

  // TODO: connect WebSocket here
}

function closeChatModal() {
  document.getElementById("chatModal").classList.add("hidden");
}

function sendChatMessage(e) {
  e.preventDefault();

  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  // TODO: send via WebSocket

  input.value = "";
}
