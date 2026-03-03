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
  const avatarSrc = conv.avatar_url || "/media/profile_photos/default-avatar.png";

  // Generate the badge HTML if the user is blocked
  // Change `conv.is_blocked` to `conv.i_blocked_them`
  const blockedBadgeHtml = conv.i_blocked_them 
    ? `<span class="px-1.5 py-0.5 rounded text-[9px] font-bold bg-red-100 text-red-600 uppercase tracking-wider shrink-0">Blocked</span>` 
    : "";

  div.innerHTML = `
    <div class="px-2 py-3 flex items-center gap-3 border-b border-gray-100">
      <img src="${avatarSrc}" class="w-12 h-12 rounded-full object-cover bg-gray-100" alt="avatar"/>
      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between gap-2">
          <div class="flex items-center gap-1 min-w-0">
              <div class="text-[15px] font-semibold text-gray-900 truncate">${escapeHtml(conv.name || "Unknown User")}</div>
              ${blockedBadgeHtml}
          </div>
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
let activeChatUsername = null; 

function openConversation(conv) {
  if (!conv || !conv.id) return;
  activeConversationId = conv.id;

  updateHeader(conv);
  document.getElementById("chatHeader")?.classList.remove("hidden");
  setEmptyState(false);

  // Disable the composer if EITHER user blocked the other
  if (conv.i_blocked_them) {
      setComposerEnabled(false);
      const input = document.getElementById("chatInput");
      if (input) input.placeholder = "You have blocked this user.";
  } else if (conv.they_blocked_me) {
      setComposerEnabled(false);
      const input = document.getElementById("chatInput");
      if (input) input.placeholder = "You cannot reply to this conversation.";
  } else {
      setComposerEnabled(true);
  }

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
  const badgeEl = document.getElementById("chatBlockedBadge");

  if (nameEl) nameEl.textContent = user.name || "Unknown";
  if (roleEl) roleEl.textContent = user.role || "";
  if (avatarEl) avatarEl.src = user.avatar_url || "/media/profile_photos/default-avatar.png";
  
  if (badgeEl) {
      // Only show the badge if I blocked them
      if (user.i_blocked_them) {
          badgeEl.classList.remove("hidden");
      } else {
          badgeEl.classList.add("hidden");
      }
  }

  activeChatUsername = user.username; 
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

    // 1. Check for standard errors
    if (data.error) {
      alert(data.error);
      return;
    }

    // 2. NEW: Handle live notifications!
    if (data.type === "notification") {
        handleRealtimeNotification(data.payload);
        return; 
    }

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

// --- Helper function to update the UI live ---
window.handleRealtimeNotification = function(notif) {
    // A. Increment the Red Badge
    const badge = document.getElementById("notificationBadge");
    if (badge) {
        let currentCount = parseInt(badge.textContent) || 0;
        currentCount += 1;
        badge.textContent = currentCount > 9 ? '9+' : currentCount;
        badge.classList.remove("hidden");
    }

    // B. Inject the new notification at the top of the dropdown list
    const list = document.getElementById("notificationList");
    if (!list) return;

    // Clear the "No new notifications" text if it's there
    if (list.innerHTML.includes("No new notifications") || list.innerHTML.includes("Loading...")) {
        list.innerHTML = "";
    }

    // Determine the icon based on the type
    let iconHtml = '';
    if (notif.notification_type === 'ENROLLMENT') {
        iconHtml = `<div class="h-8 w-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg></div>`;
    } else if (notif.notification_type === 'MATERIAL') {
        iconHtml = `<div class="h-8 w-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>`;
    }

    const newItemHtml = `
        <a href="javascript:void(0)" onclick="handleNotificationClick(null, '${notif.link}')" class="block px-4 py-3 border-b border-gray-50 bg-blue-50/30 hover:bg-blue-50/80 transition cursor-pointer">
            <div class="flex items-start gap-3">
                ${iconHtml}
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 leading-snug">${escapeHtml(notif.message)}</p>
                    <p class="text-xs text-blue-600 font-semibold mt-1">${notif.time_ago}</p>
                </div>
            </div>
        </a>
    `;

    // Insert it right at the top
    list.insertAdjacentHTML('afterbegin', newItemHtml);
};

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


/* =========================================================
   NEW CHAT / USER SEARCH FEATURE
========================================================= */
let userSearchTimeout = null;

window.toggleNewChatView = function(show) {
  const inboxView = document.getElementById("inboxView");
  const newChatView = document.getElementById("newChatView");
  const searchInput = document.getElementById("newChatSearchInput");

  if (show) {
    // Slide New Chat in, slide Inbox left
    newChatView.classList.remove("translate-x-full");
    inboxView.classList.add("-translate-x-full");
    setTimeout(() => searchInput?.focus(), 300); // Focus input after animation
  } else {
    // Slide New Chat out, slide Inbox back
    newChatView.classList.add("translate-x-full");
    inboxView.classList.remove("-translate-x-full");
    
    // Reset search
    if (searchInput) searchInput.value = "";
    document.getElementById("newChatSearchResults").innerHTML = `<div class="text-center text-sm text-gray-400 mt-10">Type a name to search users...</div>`;
  }
}

window.handleNewChatSearch = function(query) {
  clearTimeout(userSearchTimeout);
  const container = document.getElementById("newChatSearchResults");
  const cleanQuery = query.trim();

  if (!cleanQuery) {
    container.innerHTML = `<div class="text-center text-sm text-gray-400 mt-10">Type a name to search users...</div>`;
    return;
  }

  // Show a loading state
  container.innerHTML = `<div class="text-center text-sm text-gray-400 mt-10">Searching...</div>`;

  // Debounce the API call by 400ms so we don't spam the server
  userSearchTimeout = setTimeout(() => {
    // Re-using your existing generic user search endpoint
    fetch(`/users/search/?q=${encodeURIComponent(cleanQuery)}`)
      .then(res => res.json())
      .then(data => {
        container.innerHTML = "";
        
        // Assume your backend returns { "results": [...] }
        const users = data.results || [];

        // Filter out the current logged-in user so they can't chat with themselves
        const validUsers = users.filter(u => String(u.id) !== String(getCurrentUserId()));

        if (validUsers.length === 0) {
          container.innerHTML = `<div class="text-center text-sm text-gray-400 mt-10">No users found.</div>`;
          return;
        }

        const fragment = document.createDocumentFragment();
        validUsers.forEach(user => {
          const div = document.createElement("div");
          div.className = "px-4 py-3 flex items-center gap-3 hover:bg-gray-50 cursor-pointer transition";
          
          // Use avatar_url falling back to default
          const avatar = user.avatar_url || "/media/profile_photos/default-avatar.png";
          
          div.innerHTML = `
            <img src="${avatar}" class="w-10 h-10 rounded-full object-cover bg-gray-100" />
            <div class="flex-1 min-w-0">
              <div class="font-semibold text-sm text-gray-900 truncate">${escapeHtml(user.full_name || user.username)}</div>
              <div class="text-xs text-gray-500 truncate">${escapeHtml(user.email || user.role)}</div>
            </div>
          `;

          // When clicked, start the conversation
          div.onclick = () => initiateChatWithUser(user.id);
          fragment.appendChild(div);
        });

        container.appendChild(fragment);
      })
      .catch(err => {
        console.error("User search failed:", err);
        container.innerHTML = `<div class="text-center text-sm text-red-400 mt-10">Search failed.</div>`;
      });
  }, 400);
}

window.initiateChatWithUser = function(userId) {
  // Hit the start_conversation Django view you already created
  fetch(`/chat/start/${userId}/`)
    .then(res => res.json())
    .then(data => {
      if (data.error) {
        alert(data.error);
        return;
      }
      
      // Close the new chat view
      toggleNewChatView(false);

      // Reload the conversations list so the new chat appears in the inbox,
      // then open it automatically!
      loadConversations().then(() => {
        openConversationById(data.conversation_id);
      });
    })
    .catch(err => {
      console.error("Error starting chat:", err);
      alert("Unable to start conversation.");
    });
}

/* =========================================================
   CHAT MENU OPTIONS (View Profile, Clear, Block)
========================================================= */

// Helper function to grab the CSRF token for Django POST requests
function getDjangoCSRFToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, 10) === ('csrftoken=')) {
                cookieValue = decodeURIComponent(cookie.substring(10));
                break;
            }
        }
    }
    return cookieValue;
}

window.toggleChatMenu = function() {
    const menu = document.getElementById("chatOptionsMenu");
    if (!menu) return;
    menu.classList.toggle("hidden");
    menu.classList.toggle("flex");
};

// Auto-close menu if user clicks outside of it
document.addEventListener("click", (e) => {
    const menu = document.getElementById("chatOptionsMenu");
    if (menu && !menu.classList.contains("hidden")) {
        const btn = menu.previousElementSibling;
        if (!menu.contains(e.target) && !btn.contains(e.target)) {
            menu.classList.add("hidden");
            menu.classList.remove("flex");
        }
    }
});

window.viewChatUserProfile = function() {
    if (activeChatUsername) {
        // Navigates to the Django profile page
        window.location.href = `/@${encodeURIComponent(activeChatUsername)}/`;
    }
    toggleChatMenu();
};

window.clearChatHistory = function() {
    if (!activeConversationId) return;
    
    // Require confirmation so they don't do it accidentally
    if (!confirm("Are you sure you want to clear this chat? This cannot be undone.")) {
        toggleChatMenu();
        return; 
    }

    // Call your Django backend to delete the messages
    fetch(`/chat/clear/${activeConversationId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getDjangoCSRFToken(),
            "Content-Type": "application/json"
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // Instantly clear the screen
            document.getElementById("chatMessages").innerHTML = `<div class="text-center text-gray-400 text-xs mt-4">Conversation cleared.</div>`;
            updateConversationPreview(activeConversationId, "Chat cleared", null, "");
        }
        toggleChatMenu();
    });
};

window.blockChatUser = function() {
    if (!activeConversationId) return; 
    
    if (!confirm("Are you sure you want to block this user? They will no longer be able to message you.")) {
        toggleChatMenu();
        return; 
    }

    fetch(`/chat/block/${activeConversationId}/`, {
        method: "POST",
        headers: {
            "X-CSRFToken": getDjangoCSRFToken(),
            "Content-Type": "application/json"
        }
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            // 1. Update the cache
            const conv = conversationsCache.find(c => String(c.id) === String(activeConversationId));
            if (conv) {
                // Change this from is_blocked to i_blocked_them
                conv.i_blocked_them = true; 
            }
            
            // 2. Disable Composer
            setComposerEnabled(false);
            const input = document.getElementById("chatInput");
            if (input) input.placeholder = "You have blocked this user.";

            // 3. Show Header Badge
            const badgeEl = document.getElementById("chatBlockedBadge");
            if (badgeEl) badgeEl.classList.remove("hidden");

            // 4. Force the sidebar to re-render so the badge appears there too
            const list = document.getElementById("conversationList");
            if (list) {
                list.innerHTML = "";
                const fragment = document.createDocumentFragment();
                conversationsCache.forEach(c => fragment.appendChild(createConversationItem(c)));
                list.appendChild(fragment);
                highlightActive();
            }

        } else {
            alert(data.error);
        }
        toggleChatMenu();
    })
    .catch(err => {
        console.error("Block error:", err);
        toggleChatMenu();
    });
};