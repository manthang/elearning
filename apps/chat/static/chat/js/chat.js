let socket = null;
let activeChatUserId = null;
let socketReady = false;

/* =========================
   OPEN MESSENGER
========================= */

window.openMessenger = function (userId = null) {
  const panel = document.getElementById("messengerPanel");
  panel.classList.remove("hidden");

  loadConversations().then(() => {
    if (userId) {
      activateChat(userId);
    }
  });
};

window.closeMessenger = function () {
  document.getElementById("messengerPanel").classList.add("hidden");
  if (socket) {
    socket.close();
    socket = null;
  }
  socketReady = false;
};

/* =========================
   LOAD CONVERSATIONS
========================= */

function loadConversations() {
  return fetch("/chat/conversations/")
    .then(res => {
      if (!res.ok) throw new Error("Failed to load conversations");
      return res.json();
    })
    .then(data => {
      const container = document.getElementById("conversationList");
      container.innerHTML = "";

      data.conversations.forEach(c => {
        const div = document.createElement("div");
        div.className = "p-4 hover:bg-gray-100 cursor-pointer";
        div.innerHTML = `
          <p class="font-semibold text-sm">${c.name}</p>
          <p class="text-xs text-gray-500 truncate">${c.last_message || ""}</p>
        `;
        div.onclick = () => activateChat(c.user_id);
        container.appendChild(div);
      });
    })
    .catch(err => console.error(err));
}

/* =========================
   ACTIVATE CHAT
========================= */

function activateChat(userId) {
  activeChatUserId = userId;

  const container = document.getElementById("chatMessages");
  container.innerHTML = "";

  loadChatHeader(userId);
  loadChatHistory(userId);
  connectWebSocket(userId);

  requestAnimationFrame(() => {
    const input = document.getElementById("chatInput");
    if (input) input.focus();
  });
}

/* =========================
   WEBSOCKET
========================= */

function connectWebSocket(userId) {
  if (socket) socket.close();

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  socket = new WebSocket(
    `${protocol}://${window.location.host}/ws/chat/${userId}/`
  );

  socket.onopen = () => {
    socketReady = true;
  };

  socket.onmessage = e => {
    const data = JSON.parse(e.data);
    renderMessage(
      data.message,
      data.sender_id === CURRENT_USER_ID,
      data.timestamp
    );
  };

  socket.onclose = () => {
    socketReady = false;
  };

  socket.onerror = err => {
    console.error("WebSocket error:", err);
  };
}

/* =========================
   LOAD HEADER
========================= */

function loadChatHeader(userId) {
  fetch(`/accounts/profile/${userId}/`)
    .then(res => res.json())
    .then(user => {
      document.getElementById("chatAvatar").src =
        user.avatar || "/media/profile_photos/default-avatar.svg";
      document.getElementById("chatName").innerText = user.full_name;
      document.getElementById("chatRole").innerText = user.role;
    })
    .catch(err => console.error(err));
}

/* =========================
   LOAD HISTORY
========================= */

function loadChatHistory(userId) {
  fetch(`/chat/history/${userId}/`)
    .then(res => res.json())
    .then(data => {
      data.messages.forEach(m => {
        renderMessage(m.content, m.sender === CURRENT_USER_ID, m.time);
      });
    })
    .catch(err => console.error(err));
}

/* =========================
   SEND MESSAGE
========================= */

window.sendMessage = function (e) {
  if (e) e.preventDefault();
  if (!socketReady) return;

  const input = document.getElementById("chatInput");
  const message = input.value.trim();
  if (!message) return;

  socket.send(JSON.stringify({ message }));
  input.value = "";
};

/* =========================
   RENDER MESSAGE
========================= */

function renderMessage(text, isMine, timestamp = "") {
  const container = document.getElementById("chatMessages");

  const template = document.getElementById(
    isMine ? "messageMine" : "messageOther"
  );

  if (!template) return;

  const clone = template.content.cloneNode(true);
  clone.querySelector(".message-text").textContent = text;
  clone.querySelector(".message-time").textContent = timestamp;

  container.appendChild(clone);

  requestAnimationFrame(() => {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth"
    });
  });
}
