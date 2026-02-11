let socket = null;
let socketReady = false;
let activeChatUserId = null;

/* =========================
   OPEN CHAT MODAL
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

  // Delay focus slightly AFTER everything starts
  setTimeout(() => {
    focusChatInput();
  }, 100);
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

function disableSendButton(disabled) {
  const btn = document.querySelector("#chatForm button");
  if (!btn) return;

  btn.disabled = disabled;
  btn.classList.toggle("opacity-50", disabled);
  btn.classList.toggle("cursor-not-allowed", disabled);
}

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
   LOAD CHAT HISTORY
========================= */

function loadChatHistory(userId) {
  fetch(`/chat/history/${userId}/`)
    .then(res => res.json())
    .then(data => {
      data.messages.forEach(m => {
        renderMessage(m.content, m.sender === CURRENT_USER_ID, m.time);
      });
    });
}

// Auto-focus chat input
function focusChatInput() {
  const input = document.getElementById("chatInput");
  if (!input) return;

  input.disabled = false;

  input.focus({ preventScroll: true });
  input.setSelectionRange(input.value.length, input.value.length);
}


/* =========================
   CLOSE CHAT MODAL
========================= */

window.closeChatModal = function () {
  document.getElementById("chatModal").classList.add("hidden");

  if (socket) {
    socket.close();
    socket = null;
  }

  socketReady = false;
  activeChatUserId = null;
};


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

function renderMessage(text, isMine, timestamp = "") {
  const container = document.getElementById("chatMessages");

  const template = document.getElementById(
    isMine ? "messageTemplateMine" : "messageTemplateOther"
  );

  const clone = template.content.cloneNode(true);

  clone.querySelector(".message-text").textContent = text;
  clone.querySelector(".message-time").textContent = timestamp || "";

  container.appendChild(clone);

  scrollToBottom();
}

// Auto-scroll to bottom
function scrollToBottom() {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  requestAnimationFrame(() => {
    container.scrollTo({
      top: container.scrollHeight,
      behavior: "smooth"
    });
  });
}
