let socket = null;
let socketReady = false;
let activeChatUserId = null;

/* =========================
   OPEN / CLOSE CHAT MODAL
========================= */

window.openChatModal = function (userId) {
  activeChatUserId = userId;
  socketReady = false;

  document.getElementById("chatModal").classList.remove("hidden");
  document.getElementById("chatMessages").innerHTML = "";

  disableSendButton(true);

  connectWebSocket(userId);
  loadChatHeader(userId);
  loadChatHistory(userId);
};

function connectWebSocket(userId) {
  if (socket) {
    socket.close();
  }

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(
    `${protocol}://${window.location.host}/ws/chat/${userId}/`
  );

  socket.onopen = () => {
    console.log("✅ WebSocket OPEN");
    socketReady = true;
    disableSendButton(false);
  };

  socket.onmessage = (e) => {
    const data = JSON.parse(e.data);
    renderMessage(
      data.message,
      data.sender_id === CURRENT_USER_ID,
      data.timestamp
    );
  };

  socket.onclose = () => {
    console.log("⚠️ WebSocket CLOSED");
    socketReady = false;
    disableSendButton(true);
  };

  socket.onerror = (err) => {
    console.error("WebSocket error", err);
    socketReady = false;
    disableSendButton(true);
  };
}

function loadChatHistory(userId) {
  fetch(`/chat/history/${userId}/`)
    .then(res => res.json())
    .then(data => {
      data.messages.forEach(m => {
        renderMessage(m.content, m.sender === CURRENT_USER_ID, m.time);
      });
    });
}

window.closeChatModal = function () {
  document.getElementById("chatModal").classList.add("hidden");
  activeChatUserId = null;
};

/* =========================
   LOAD CHAT HEADER (TARGET USER)
========================= */

function loadChatHeader(userId) {
  fetch(`/accounts/profile/${userId}/`)
    .then(res => res.json())
    .then(user => {
      document.getElementById("chatAvatar").src =
        user.avatar || "/media/profile_photos/default-avatar.png";

      document.getElementById("chatName").innerText = user.full_name;
      document.getElementById("chatRole").innerText = user.role;
    })
    .catch(() => {
      document.getElementById("chatName").innerText = "Unknown user";
      document.getElementById("chatRole").innerText = "";
    });
}

/* =========================
   SEND MESSAGE
========================= */

window.sendMessage = function (event) {
  if (event) event.preventDefault();

  if (!socket || !socketReady) {
    console.warn("WebSocket not ready");
    return;
  }

  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  socket.send(JSON.stringify({ message }));
  input.value = "";
};

function renderMessage(text, mine, time) {
  const bubble = document.createElement("div");
  bubble.className = mine
    ? "self-end bg-blue-600 text-white px-4 py-2 rounded-xl"
    : "self-start bg-white border px-4 py-2 rounded-xl";

  bubble.innerHTML = `<p>${text}</p><span class="text-xs opacity-70">${time}</span>`;
  document.getElementById("chatMessages").appendChild(bubble);
}

function disableSendButton(disabled) {
  const btn = document.querySelector("#chatForm button");
  if (!btn) return;

  btn.disabled = disabled;
  btn.classList.toggle("opacity-50", disabled);
  btn.classList.toggle("cursor-not-allowed", disabled);
}
