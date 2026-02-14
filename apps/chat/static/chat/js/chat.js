let activeConversationId = null;
let conversationsCache = [];
let inboxSocket = null;

const unreadCounts = new Map();
const seenMessageIds = new Set();

window.openMessenger = function (conversationId = null) {
  const panel = document.getElementById("messengerPanel");
  const box = document.getElementById("messengerBox");

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

  connectInboxSocket();

  loadConversations().then(() => {
    wireSearch();
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

function loadConversations() {
  return fetch("/chat/conversations/")
    .then(res => res.json())
    .then(data => {
      const list = document.getElementById("conversationList");
      if (!list) return;

      list.innerHTML = "";
      conversationsCache = data.conversations || [];

      conversationsCache.forEach(conv => list.appendChild(createConversationItem(conv)));
      highlightActive();

      return conversationsCache;
    })
    .catch(err => console.error("Conversation load error:", err));
}

function createConversationItem(conv) {
  const div = document.createElement("div");
  div.dataset.id = conv.id;

  const isMine = String(conv.sender_id) === String(CURRENT_USER_ID);
  const previewText = conv.last_message
    ? (isMine ? `You: ${conv.last_message}` : conv.last_message)
    : "";

  div.className = buildConversationItemClass(conv.id);

  div.innerHTML = `
    <div class="px-2 py-3 flex items-center gap-3 border-b border-gray-100">
      <img src="${conv.avatar || "/media/profile_photos/default-avatar.svg"}"
           class="w-12 h-12 rounded-full object-cover bg-gray-100"
           alt="avatar"/>

      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2">
          <div class="text-[15px] font-semibold text-gray-900 truncate">
            ${escapeHtml(conv.name || "")}
          </div>
          <div class="text-[11px] text-gray-400 convo-time">
            ${escapeHtml(conv.time || "")}
          </div>
        </div>

        <div class="flex items-center justify-between gap-2 mt-0.5">
          <div class="text-[13px] text-gray-600 truncate last-message">
            ${escapeHtml(previewText)}
          </div>

          <span class="unread-badge hidden text-[11px] leading-none px-2 py-1 rounded-full bg-[#00a884] text-white font-semibold">
            0
          </span>
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

  let cls = `
    cursor-pointer select-none
    px-2
    transition
  `;

  // WhatsApp-like row feel
  cls += isActive ? " bg-gray-100 " : " hover:bg-gray-50 ";

  return cls;
}

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

  if (!nameEl || !roleEl || !avatarEl) return;

  nameEl.textContent = user.name || "";
  roleEl.textContent = user.role ? user.role : "";
  avatarEl.src = user.avatar ?? "/media/profile_photos/default-avatar.svg";
}

function loadChatHistory(conversationId) {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  container.innerHTML = "<div class='text-white/40 text-sm'>Loading...</div>";

  fetch(`/chat/history/${conversationId}/`)
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";
      (data.messages || []).forEach(msg => {
        if (msg.id) seenMessageIds.add(String(msg.id));
        renderMessage(msg.content, msg.sender_id === CURRENT_USER_ID, msg.created_at);
      });
      scrollToBottom();
      focusInput();
    })
    .catch(err => console.error("History error:", err));
}

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
      renderMessage(data.message, data.sender_id === CURRENT_USER_ID, data.created_at);
      scrollToBottom();
      return;
    }

    const prev = unreadCounts.get(conversationId) || 0;
    unreadCounts.set(conversationId, prev + 1);
    renderUnreadBadge(conversationId);
  };
}

function disconnectInboxSocket() {
  if (inboxSocket) {
    inboxSocket.close();
    inboxSocket = null;
  }
}

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

  // Optimistic preview (time optional)
  updateConversationPreview(String(activeConversationId), message, CURRENT_USER_ID, "");
  moveConversationToTop(String(activeConversationId));
  focusInput();
};

function updateConversationPreview(conversationId, message, senderId = null, timeStr = "") {
  const item = document.querySelector(`#conversationList > div[data-id="${conversationId}"]`);
  if (!item) return;

  const preview = item.querySelector(".last-message");
  const timeEl = item.querySelector(".convo-time");

  if (preview) {
    const isMine = String(senderId) === String(CURRENT_USER_ID);
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
    badge.textContent = String(count);
  } else {
    badge.classList.add("hidden");
    badge.textContent = "0";
  }
}

function highlightActive() {
  document.querySelectorAll("#conversationList > div").forEach(div => {
    const id = div.dataset.id;
    div.className = buildConversationItemClass(id);
  });
}

function renderMessage(message, isMine, timeStr = "") {
  const container = document.getElementById("chatMessages");
  if (!container) return;

  const wrapper = document.createElement("div");
  wrapper.className = `flex ${isMine ? "justify-end" : "justify-start"}`;

  const bubbleClass = isMine
    ? "bg-[#d9fdd3] text-gray-900 rounded-lg rounded-tr-sm"
    : "bg-white text-gray-900 rounded-lg rounded-tl-sm border border-black/5";

  const timeHtml = timeStr
    ? `<span class="ml-2 text-[10px] text-gray-500 whitespace-nowrap">${escapeHtml(timeStr)}</span>`
    : "";

  wrapper.innerHTML = `
    <div class="max-w-[72%] px-3 py-2 text-[14px] leading-snug shadow-[0_1px_0_rgba(0,0,0,0.08)] ${bubbleClass}">
      <span>${escapeHtml(message)}</span>
      ${timeHtml}
    </div>
  `;

  container.appendChild(wrapper);
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
  if (!empty) return;
  empty.classList.toggle("hidden", !isEmpty);
}

function setComposerEnabled(enabled) {
  const input = document.getElementById("chatInput");
  const btn = document.getElementById("chatSendBtn");
  if (!input || !btn) return;

  input.disabled = !enabled;
  btn.disabled = !enabled;

  input.placeholder = enabled ? "Type a message" : "Select a conversation to start typing…";
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

    filtered.forEach(conv => list.appendChild(createConversationItem(conv)));
    highlightActive();
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
