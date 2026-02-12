/* ================================
   GLOBAL STATE
================================ */
let activeConversationId = null;
let socket = null;

/* ================================
   OPEN / CLOSE MESSENGER
================================ */

window.openMessenger = function (conversationId = null) {
  const panel = document.getElementById("messengerPanel");
  if (!panel) return;

  panel.classList.remove("hidden");

  loadConversations().then(() => {
    if (conversationId) {
      openConversationById(conversationId);
    }
  });
};

window.closeMessenger = function () {
  const panel = document.getElementById("messengerPanel");
  if (!panel) return;

  panel.classList.add("hidden");

  disconnectSocket();
  activeConversationId = null;
};

/* ================================
   LOAD CONVERSATIONS
================================ */

function loadConversations() {
  return fetch("/chat/conversations/")
    .then(res => res.json())
    .then(data => {
      const list = document.getElementById("conversationList");
      if (!list) return;

      list.innerHTML = "";

      const conversations = data.conversations || [];

      conversations.forEach(conv => {
        const div = document.createElement("div");
        div.className = `
          px-4 py-3 border-b cursor-pointer hover:bg-gray-100
          ${conv.id === activeConversationId ? "bg-gray-100" : ""}
        `;

        div.dataset.id = conv.id;

        div.innerHTML = `
          <div class="flex items-center gap-3">
            <img src="${conv.avatar || "/media/profile_photos/default-avatar.svg"}"
                 class="w-8 h-8 rounded-full object-cover" />

            <div>
              <div class="font-medium text-sm">${conv.name}</div>
              <div class="text-xs text-gray-500 truncate">
                ${conv.last_message || ""}
              </div>
            </div>
          </div>
        `;

        div.onclick = () => openConversation(conv);

        list.appendChild(div);
      });

      return conversations;
    })
    .catch(err => console.error("Conversation load error:", err));
}

/* ================================
   OPEN CONVERSATION
================================ */

function openConversation(conv) {
  if (!conv || !conv.id) {
    console.error("Invalid conversation:", conv);
    return;
  }

  activeConversationId = conv.id;

  updateHeader(conv);
  loadChatHistory(conv.id);
  connectWebSocket(conv.id);
  highlightActive();
}

function openConversationById(conversationId) {
  fetch("/chat/conversations/")
    .then(res => res.json())
    .then(data => {
      const conv = data.conversations.find(c => c.id == conversationId);
      if (conv) openConversation(conv);
    });
}

/* ================================
   UPDATE HEADER
================================ */

function updateHeader(user) {
  const nameEl = document.getElementById("chatName");
  const roleEl = document.getElementById("chatRole");
  const avatarEl = document.getElementById("chatAvatar");

  if (!nameEl || !roleEl || !avatarEl) return;

  nameEl.textContent = user.name;
  roleEl.textContent = user.role
    ? user.role.charAt(0).toUpperCase() + user.role.slice(1).toLowerCase()
    : "";

  avatarEl.src = user.avatar ?? "/media/profile_photos/default-avatar.svg";
}

/* ================================
   LOAD HISTORY
================================ */

function loadChatHistory(conversationId) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  container.innerHTML = "<div class='text-gray-400 text-sm'>Loading...</div>";

  fetch(`/chat/history/${conversationId}/`)
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";

      data.messages.forEach(msg => {
        renderMessage(msg.content, msg.sender_id === CURRENT_USER_ID);
      });

      scrollToBottom();
      focusInput();
    })
    .catch(err => console.error("History error:", err));
}

/* ================================
   WEBSOCKET
================================ */

function connectWebSocket(conversationId) {
  disconnectSocket();

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";

  socket = new WebSocket(
    `${protocol}://${window.location.host}/ws/chat/${conversationId}/`
  );

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    renderMessage(
      data.message,
      data.sender_id === CURRENT_USER_ID
    );

    scrollToBottom();
  };
}

function disconnectSocket() {
  if (socket) {
    socket.close();
    socket = null;
  }
}

/* ================================
   SEND MESSAGE
================================ */

window.sendMessage = function () {
  const input = document.getElementById("chatInput");
  if (!input || !socket || socket.readyState !== WebSocket.OPEN) return;

  const message = input.value.trim();
  if (!message) return;

  socket.send(JSON.stringify({ message }));
  input.value = "";
};

/* ================================
   UI HELPERS
================================ */

function renderMessage(message, isMine) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const wrapper = document.createElement("div");
  wrapper.className = `flex ${isMine ? "justify-end" : "justify-start"}`;

  wrapper.innerHTML = `
    <div class="
      max-w-md px-4 py-2 rounded-xl text-sm
      ${isMine
        ? "bg-blue-600 text-white rounded-br-none"
        : "bg-white text-gray-800 border rounded-bl-none"}
    ">
      ${message}
    </div>
  `;

  container.appendChild(wrapper);
}

function scrollToBottom() {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  requestAnimationFrame(() => {
    container.scrollTop = container.scrollHeight;
  });
}

function focusInput() {
  setTimeout(() => {
    const input = document.getElementById("chatInput");
    if (input) input.focus();
  }, 100);
}

function highlightActive() {
  document.querySelectorAll("#conversationList > div")
    .forEach(div => {
      div.classList.remove("bg-gray-100");
      if (div.dataset.id == activeConversationId) {
        div.classList.add("bg-gray-100");
      }
    });
}
