/* =========================================================
   STATE MANAGEMENT & GETTERS
========================================================= */
let activeConversationId = null;
let conversationsCache = [];
let inboxSocket = null;
let reconnectTimer = null;

const unreadCounts = new Map();
const seenMessageIds = new Set();

// Dynamic getter to ensure we always have the latest ID from the template
function getCurrentUserId() {
  const id = window.CURRENT_USER_ID || null;
  if (!id) {
    console.warn("window.CURRENT_USER_ID is not defined yet.");
  }
  return id;
}

/* =========================================================
   UI TOGGLES
========================================================= */
window.openMessenger = function (conversationId = null) {
  const panel = document.getElementById("messengerPanel");
  const box = document.getElementById("messengerBox");
  if (!panel || !box) return;

  panel.classList.remove("hidden");
  panel.classList.add("flex");

  requestAnimationFrame(() => {
    panel.classList.remove("opacity-0");
    box.classList.remove("opacity-0", "scale-95");
    box.classList.add("opacity-100", "scale-100");
  });

  // Reset UI
  activeConversationId = null;
  document.getElementById("chatHeader")?.classList.add("hidden");
  setEmptyState(true);
  setComposerEnabled(false);

  // Show loading state in sidebar
  const list = document.getElementById("conversationList");
  if (list) list.innerHTML = `<div class="p-4 text-center text-sm text-gray-400">Loading chats...</div>`;

  connectInboxSocket();

  loadConversations().then(() => {
    wireSearch();
    if (conversationId) openConversationById(conversationId);
  });
};

window.closeMessenger = function () {
  const panel = document.getElementById("messengerPanel");
  const box = document.getElementById("messengerBox");
  if (!panel || !box) return;

  panel.classList.add("opacity-0");
  box.classList.add("opacity-0", "scale-95");

  setTimeout(() => {
    panel.classList.add("hidden");
    panel.classList.remove("flex");
    disconnectInboxSocket();
  }, 200);
};

/* =========================================================
   CONVERSATION LIST
========================================================= */
function loadConversations() {
  return fetch("/chat/conversations/")
    .then(res => res.json())
    .then(data => {
      const list = document.getElementById("conversationList");
      if (!list) return;

      list.innerHTML = "";
      conversationsCache = data.conversations || [];

      if (conversationsCache.length === 0) {
        list.innerHTML = `<div class="p-4 text-center text-sm text-gray-400">No conversations yet.</div>`;
        return conversationsCache;
      }

      const fragment = document.createDocumentFragment();
      conversationsCache.forEach(conv => fragment.appendChild(createConversationItem(conv)));
      list.appendChild(fragment);
      
      highlightActive();
      return conversationsCache;
    })
    .catch(err => {
      console.error("Conversation load error:", err);
      const list = document.getElementById("conversationList");
      if (list) list.innerHTML = `<div class="p-4 text-center text-sm text-red-400">Failed to load.</div>`;
    });
}

function createConversationItem(conv) {
  const div = document.createElement("div");
  div.dataset.id = conv.id;

  const isMine = String(conv.sender_id) === String(getCurrentUserId());
  const previewText = conv.last_message
    ? (isMine ? `You: ${conv.last_message}` : conv.last_message)
    : "Started a new conversation";

  div.className = buildConversationItemClass(conv.id);

  // Use avatar_url to match Django properties consistently
  const avatarSrc = conv.avatar_url || "/media/profile_photos/default-avatar.png";

  div.innerHTML = `
    <div class="px-2 py-3 flex items-center gap-3 border-b border-gray-100">
      <img src="${avatarSrc}" class="w-12 h-12 rounded-full object-cover bg-gray-100" alt="avatar"/>
      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2">
          <div class="text-[15px] font-semibold text-gray-900 truncate">${escapeHtml(conv.name || "Unknown User")}</div>
          <div class="text-[11px] text-gray-400 convo-time">${escapeHtml(conv.time || "")}</div>
        </div>
        <div class="flex items-center justify-between gap-2 mt-0.5">
          <div class="text-[13px] text-gray-600 truncate last-message">${escapeHtml(previewText)}</div>
          <span class="unread-badge hidden text-[11px] leading-none px-2 py-1 rounded-full bg-[#00a884] text-white font-semibold shadow-sm">0</span>
        </div>
      </div>
    </div>
  `;

  div.onclick = () => openConversation(conv);
  renderUnreadBadge(conv.id);

  return div;
}

function buildConversationItemClass(conversationId) {
  const isActive = String(conversationId) === String(activeConversationId);
  return `cursor-pointer select-none px-2 transition ${isActive ? "bg-gray-100" : "hover:bg-gray-50"}`;
}

/* =========================================================
   ACTIVE CONVERSATION & MESSAGES
========================================================= */
function openConversation(conv) {
  if (!conv || !conv.id) return;
  activeConversationId = conv.id;

  updateHeader(conv);
  document.getElementById("chatHeader")?.classList.remove("hidden");

  setEmptyState(false);
  setComposerEnabled(true);

  loadChatHistory(conv.id);

  unreadCounts.set(String(conv.id), 0);
  renderUnreadBadge(conv.id);
  highlightActive();
}

function openConversationById(conversationId) {
  const conv = conversationsCache.find(c => String(c.id) === String(conversationId));
  if (conv) openConversation(conv);
}

function updateHeader(user) {
  const nameEl = document.getElementById("chatName");
  const roleEl = document.getElementById("chatRole");
  const avatarEl = document.getElementById("chatAvatar");

  if (nameEl) nameEl.textContent = user.name || "Unknown";
  if (roleEl) roleEl.textContent = user.role || "";
  if (avatarEl) avatarEl.src = user.avatar_url || "/media/profile_photos/default-avatar.png";
}

function loadChatHistory(conversationId) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  container.innerHTML = `<div class="flex items-center justify-center h-full text-gray-400 text-sm">Loading history...</div>`;

  fetch(`/chat/history/${conversationId}/`)
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      
      if (!data.messages || data.messages.length === 0) {
        container.innerHTML = `<div class="text-center text-gray-400 text-xs mt-4">This is the start of your conversation.</div>`;
        return;
      }

      // Batch render messages using DocumentFragment for high performance
      const fragment = document.createDocumentFragment();
      data.messages.forEach(msg => {
        if (msg.id) seenMessageIds.add(String(msg.id));
        fragment.appendChild(buildMessageDOM(msg.content, String(msg.sender_id) === String(getCurrentUserId()), msg.created_at));
      });
      container.appendChild(fragment);

      scrollToBottom();
      focusInput();
    })
    .catch(err => {
      console.error("History error:", err);
      container.innerHTML = `<div class="text-center text-red-400 text-sm mt-4">Could not load messages.</div>`;
    });
}

function buildMessageDOM(message, isMine, timeStr = "") {
  const wrapper = document.createElement("div");
  // CRITICAL FIX: Added 'w-full' to ensure justify-end actually pushes the bubble to the right
  wrapper.className = `flex mb-3 w-full ${isMine ? "justify-end" : "justify-start"}`;

  const bubbleClass = isMine
    ? "bg-[#d9fdd3] text-gray-900 rounded-lg rounded-tr-sm"
    : "bg-white text-gray-900 rounded-lg rounded-tl-sm border border-black/5";

  const timeHtml = timeStr
    ? `<span class="ml-2 mt-1 text-[10px] text-gray-500 float-right">${escapeHtml(timeStr)}</span>`
    : "";

  wrapper.innerHTML = `
    <div class="max-w-[75%] px-3 py-2 text-[14px] leading-snug shadow-sm flex flex-col ${bubbleClass}">
      <span class="break-words">${escapeHtml(message)}</span>
      ${timeHtml}
    </div>
  `;
  return wrapper;
}

function renderMessage(message, isMine, timeStr = "") {
  const container = document.getElementById("chatMessages");
  if (!container) return;
  
  // Remove empty state text if it exists
  const firstChild = container.firstElementChild;
  if (firstChild && firstChild.innerText.includes("start of your conversation")) {
    container.innerHTML = "";
  }

  container.appendChild(buildMessageDOM(message, isMine, timeStr));
  scrollToBottom();
}

/* =========================================================
   WEBSOCKETS
========================================================= */
function connectInboxSocket() {
  if (inboxSocket && inboxSocket.readyState === WebSocket.OPEN) return;

  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  inboxSocket = new WebSocket(`${protocol}://${window.location.host}/ws/chat/inbox/`);

  inboxSocket.onmessage = (event) => {
    let data;
    try { data = JSON.parse(event.data); } catch { return; }

    const conversationId = String(data.conversation_id);
    const messageId = data.message_id ? String(data.message_id) : null;

    if (messageId && seenMessageIds.has(messageId)) return;
    if (messageId) seenMessageIds.add(messageId);

    if (data.message) {
      updateConversationPreview(conversationId, data.message, data.sender_id, data.created_at);
      moveConversationToTop(conversationId);
    }

    if (String(activeConversationId) === conversationId) {
      renderMessage(data.message, String(data.sender_id) === String(getCurrentUserId()), data.created_at);
      return;
    }

    const prev = unreadCounts.get(conversationId) || 0;
    unreadCounts.set(conversationId, prev + 1);
    renderUnreadBadge(conversationId);
  };

  inboxSocket.onclose = () => {
    console.warn("Chat connection lost. Reconnecting in 3s...");
    reconnectTimer = setTimeout(connectInboxSocket, 3000);
  };
}

function disconnectInboxSocket() {
  if (reconnectTimer) clearTimeout(reconnectTimer);
  if (inboxSocket) {
    inboxSocket.onclose = null; // Prevent auto-reconnect trigger
    inboxSocket.close();
    inboxSocket = null;
  }
}

window.sendMessage = function (event) {
  if (event) event.preventDefault();

  const input = document.getElementById("chatInput");
  if (!input) return;

  const message = input.value.trim();
  if (!message || !activeConversationId) return;

  if (!inboxSocket || inboxSocket.readyState !== WebSocket.OPEN) {
    alert("Not connected to chat server. Trying to reconnect...");
    return;
  }

  // 1. Send to server
  inboxSocket.send(JSON.stringify({
    type: "send",
    conversation_id: activeConversationId,
    message: message
  }));

  // 2. Clear input
  input.value = "";

  // 3. Update the sidebar preview instantly (this is fine because it just overwrites text)
  const localTime = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  updateConversationPreview(String(activeConversationId), message, getCurrentUserId(), localTime);
  moveConversationToTop(String(activeConversationId));
  
  // REMOVED: renderMessage(...) 
  // We now let the inboxSocket.onmessage handler draw the bubble when the server confirms it.

  focusInput();
};

/* =========================================================
   UTILITIES & HELPERS
========================================================= */
function updateConversationPreview(conversationId, message, senderId = null, timeStr = "") {
  const item = document.querySelector(`#conversationList > div[data-id="${conversationId}"]`);
  if (!item) return;

  const preview = item.querySelector(".last-message");
  const timeEl = item.querySelector(".convo-time");

  if (preview) {
    const isMine = String(senderId) === String(getCurrentUserId());
    preview.textContent = isMine ? `You: ${message}` : message;
  }
  if (timeEl && timeStr) timeEl.textContent = timeStr;

  const conv = conversationsCache.find(c => String(c.id) === String(conversationId));
  if (conv) {
    conv.last_message = message;
    conv.sender_id = senderId;
    if (timeStr) conv.time = timeStr;
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

  if (count > 0 && !isActive) {
    badge.classList.remove("hidden");
    badge.textContent = String(count > 99 ? "99+" : count);
  } else {
    badge.classList.add("hidden");
    badge.textContent = "0";
  }
}

function highlightActive() {
  document.querySelectorAll("#conversationList > div").forEach(div => {
    div.className = buildConversationItemClass(div.dataset.id);
  });
}

function scrollToBottom() {
  const container = document.getElementById("chatMessages");
  if (!container) return;
  requestAnimationFrame(() => { container.scrollTop = container.scrollHeight; });
}

function focusInput() {
  setTimeout(() => {
    const input = document.getElementById("chatInput");
    if (input && !input.disabled) input.focus();
  }, 100);
}

function setEmptyState(isEmpty) {
  const empty = document.getElementById("chatEmptyState");
  const messages = document.getElementById("chatMessages");
  if (empty) empty.classList.toggle("hidden", !isEmpty);
  if (messages) messages.classList.toggle("hidden", isEmpty);
}

function setComposerEnabled(enabled) {
  const input = document.getElementById("chatInput");
  const btn = document.getElementById("chatSendBtn");
  if (!input || !btn) return;

  input.disabled = !enabled;
  btn.disabled = !enabled;
  input.placeholder = enabled ? "Type a message..." : "Select a conversation to start typing...";
}

function wireSearch() {
  const search = document.getElementById("chatSearch");
  if (!search || search.dataset.wired === "1") return;
  search.dataset.wired = "1";

  search.addEventListener("input", () => {
    const q = (search.value || "").trim().toLowerCase();
    const list = document.getElementById("conversationList");
    if (!list) return;

    list.innerHTML = "";
    const filtered = !q
      ? conversationsCache
      : conversationsCache.filter(c =>
          (c.name || "").toLowerCase().includes(q) ||
          (c.last_message || "").toLowerCase().includes(q)
        );

    if (filtered.length === 0) {
      list.innerHTML = `<div class="p-4 text-center text-sm text-gray-400">No matches found.</div>`;
    } else {
      const fragment = document.createDocumentFragment();
      filtered.forEach(conv => fragment.appendChild(createConversationItem(conv)));
      list.appendChild(fragment);
    }
    highlightActive();
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}