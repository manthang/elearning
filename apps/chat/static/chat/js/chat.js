/* ================================
   GLOBAL STATE
================================ */
let activeConversationId = null;
let conversationsCache = [];
let inboxSocket = null;

// Track unread counts + dedupe
const unreadCounts = new Map();                 // conversationId -> count
const seenMessageIds = new Set();               // message_id global (good enough for MVP)

/* ================================
   OPEN / CLOSE MESSENGER
================================ */

window.openMessenger = function (conversationId = null) {
  const panel = document.getElementById("messengerPanel");
  const box = document.getElementById("messengerBox");

  panel.classList.remove("hidden");
  panel.classList.add("flex");

  requestAnimationFrame(() => {
    panel.classList.remove("opacity-0");
    box.classList.remove("opacity-0", "scale-95");
    box.classList.add("scale-100", "opacity-100");
  });

  connectInboxSocket();

  loadConversations().then(() => {
    if (conversationId) openConversationById(conversationId);
  });
};

window.closeMessenger = function () {
  const panel = document.getElementById("messengerPanel");
  const box = document.getElementById("messengerBox");

  panel.classList.add("opacity-0");
  box.classList.add("opacity-0", "scale-95");

  setTimeout(() => {
    panel.classList.add("hidden");
    panel.classList.remove("flex");
    disconnectInboxSocket();
  }, 200);
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
      conversationsCache = data.conversations || [];

      conversationsCache.forEach(conv => {
        const div = createConversationItem(conv);
        list.appendChild(div);
      });

      // Ensure active highlight stays correct after reload
      highlightActive();

      return conversationsCache;
    })
    .catch(err => console.error("Conversation load error:", err));
}

function createConversationItem(conv) {
  const div = document.createElement("div");

  const isMine = String(conv.sender_id) === String(CURRENT_USER_ID);
  const previewText = conv.last_message
    ? (isMine ? `You: ${conv.last_message}` : conv.last_message)
    : "";

  div.dataset.id = conv.id;

  // Card-like item, modern hover and active styles.
  // Unread styles applied in renderUnreadBadge().
  div.className = buildConversationItemClass(conv.id);

  div.innerHTML = `
    <div class="flex items-center gap-3 px-3 py-3">
      <img src="${conv.avatar || "/media/profile_photos/default-avatar.svg"}"
          class="w-9 h-9 rounded-full object-cover bg-white"
          alt="avatar" />

      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2">
          <div class="font-semibold text-sm text-gray-900 truncate">
            ${escapeHtml(conv.name || "")}
          </div>

          <span class="unread-badge hidden text-[10px] leading-none px-2 py-1 rounded-full bg-blue-600 text-white">
            0
          </span>
        </div>

        <div class="text-xs text-gray-500 truncate last-message">
          ${escapeHtml(previewText)}
        </div>
      </div>
    </div>
  `;

  div.onclick = () => openConversation(conv);

  // Apply existing unread state
  renderUnreadBadge(conv.id);

  return div;
}

function buildConversationItemClass(conversationId) {
  const isActive = String(conversationId) === String(activeConversationId);

  // base card
  let cls = `
    rounded-2xl bg-white/70 backdrop-blur-sm
    cursor-pointer select-none
    transition-all duration-150
    hover:bg-white hover:shadow-sm
  `;

  // active state
  if (isActive) {
    cls += ` ring-2 ring-blue-200 bg-white shadow-sm `;
  }

  return cls;
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

  // Clear unread when opening
  unreadCounts.set(String(conv.id), 0);
  renderUnreadBadge(conv.id);

  highlightActive();
}

function openConversationById(conversationId) {
  const conv = conversationsCache.find(c => String(c.id) === String(conversationId));
  if (conv) openConversation(conv);
}

/* ================================
   UPDATE HEADER
================================ */

function updateHeader(user) {
  const nameEl = document.getElementById("chatName");
  const roleEl = document.getElementById("chatRole");
  const avatarEl = document.getElementById("chatAvatar");

  if (!nameEl || !roleEl || !avatarEl) return;

  nameEl.textContent = user.name || "Conversation";
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

      (data.messages || []).forEach(msg => {
        if (msg.id) seenMessageIds.add(String(msg.id));
        renderMessage(msg.content, msg.sender_id === CURRENT_USER_ID);
      });

      scrollToBottom();
      focusInput();
    })
    .catch(err => console.error("History error:", err));
}

/* ================================
   INBOX WEBSOCKET (ONE SOCKET FOR ALL CONVERSATIONS)
================================ */

function connectInboxSocket() {
  if (inboxSocket && inboxSocket.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  inboxSocket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/inbox/`);

  inboxSocket.onmessage = (event) => {
    let data;
    try {
      data = JSON.parse(event.data);
    } catch (e) {
      return;
    }

    const conversationId = String(data.conversation_id);
    const messageId = data.message_id ? String(data.message_id) : null;

    // Dedup
    if (messageId && seenMessageIds.has(messageId)) return;
    if (messageId) seenMessageIds.add(messageId);

    // Update preview + reorder list
    if (data.message) {
      updateConversationPreview(conversationId, data.message, data.sender_id);
      moveConversationToTop(conversationId);
    }

    // If it's the active conversation, render it into the message area
    if (String(activeConversationId) === conversationId) {
      renderMessage(data.message, data.sender_id === CURRENT_USER_ID);
      scrollToBottom();
      return;
    }

    // Otherwise increment unread and show badge
    const prev = unreadCounts.get(conversationId) || 0;
    unreadCounts.set(conversationId, prev + 1);
    renderUnreadBadge(conversationId);
  };

  inboxSocket.onclose = () => {
    // reconnect next time modal opens
  };
}

function disconnectInboxSocket() {
  if (inboxSocket) {
    inboxSocket.close();
    inboxSocket = null;
  }
}

/* ================================
   SEND MESSAGE (via inbox socket)
================================ */

window.sendMessage = function (event) {
  if (event) event.preventDefault();

  const input = document.getElementById("chatInput");
  if (!input) return;

  const message = input.value.trim();
  if (!message) return;

  if (!activeConversationId) return;
  if (!inboxSocket || inboxSocket.readyState !== WebSocket.OPEN) return;

  inboxSocket.send(JSON.stringify({
    type: "send",
    conversation_id: activeConversationId,
    message: message
  }));

  input.value = "";

  // Optimistic UI updates
  updateConversationPreview(String(activeConversationId), message, CURRENT_USER_ID);
  moveConversationToTop(String(activeConversationId));

  focusInput();
};

/* ================================
   CONVERSATION LIST UPDATES
================================ */

function updateConversationPreview(conversationId, message, senderId = null) {
  const item = document.querySelector(
    `#conversationList > div[data-id="${conversationId}"]`
  );
  if (!item) return;

  const preview = item.querySelector(".last-message");
  if (!preview) return;

  const isMine = String(senderId) === String(CURRENT_USER_ID);
  preview.textContent = isMine ? `You: ${message}` : message;

  const conv = conversationsCache.find(c => String(c.id) === String(conversationId));
  if (conv) {
    conv.last_message = message;
    conv.sender_id = senderId;
  }
}

function moveConversationToTop(conversationId) {
  const list = document.getElementById("conversationList");
  const item = document.querySelector(`#conversationList > div[data-id="${conversationId}"]`);
  if (!list || !item) return;

  list.prepend(item);
  highlightActive();
}

function renderUnreadBadge(conversationId) {
  const item = document.querySelector(`#conversationList > div[data-id="${conversationId}"]`);
  if (!item) return;

  const badge = item.querySelector(".unread-badge");
  if (!badge) return;

  const count = unreadCounts.get(String(conversationId)) || 0;
  const isActive = String(activeConversationId) === String(conversationId);

  // Reset base class to keep active style correct, then overlay unread style
  item.className = buildConversationItemClass(conversationId);

  if (count > 0 && !isActive) {
    badge.classList.remove("hidden");
    badge.textContent = String(count);

    // Soft unread glow
    item.className += ` ring-2 ring-blue-100 `;
  } else {
    badge.classList.add("hidden");
    badge.textContent = "0";
  }
}

/* ================================
   UI HELPERS
================================ */

function renderMessage(message, isMine) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const wrapper = document.createElement("div");
  wrapper.className = `flex ${isMine ? "justify-end" : "justify-start"}`;

  // Match the updated template vibe:
  // - Mine: gradient bubble
  // - Other: soft white bubble
  wrapper.innerHTML = `
    <div class="
      max-w-md px-4 py-2 text-sm
      ${isMine
        ? "bg-gradient-to-br from-blue-600 to-blue-500 text-white rounded-2xl rounded-br-sm shadow-md"
        : "bg-white/90 backdrop-blur-sm text-gray-900 rounded-2xl rounded-bl-sm shadow-sm"}
    ">
      ${escapeHtml(message)}
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
  document.querySelectorAll("#conversationList > div").forEach(div => {
    const id = div.dataset.id;
    div.className = buildConversationItemClass(id);

    // Reapply unread visual if needed
    const count = unreadCounts.get(String(id)) || 0;
    const isActive = String(activeConversationId) === String(id);
    if (count > 0 && !isActive) {
      div.className += ` ring-2 ring-blue-100 `;
    }
  });
}

function escapeHtml(str) {
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
