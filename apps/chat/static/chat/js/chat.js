let activeChatUserId = null;

/* =========================
   OPEN / CLOSE CHAT MODAL
========================= */

window.openChatModal = function (userId) {
  activeChatUserId = userId;

  document.getElementById("chatModal").classList.remove("hidden");
  document.getElementById("chatMessages").innerHTML = "";

  loadChatHeader(userId);
  // loadChatHistory(userId); // ← hook WebSocket / AJAX here later
};

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
   SEND MESSAGE (PLACEHOLDER)
========================= */

window.sendMessage = function () {
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text || !activeChatUserId) return;

  const bubble = document.createElement("div");
  bubble.className =
    "self-end bg-blue-600 text-white px-4 py-2 rounded-lg max-w-[80%]";
  bubble.innerText = text;

  document.getElementById("chatMessages").appendChild(bubble);
  input.value = "";

  // TODO:
  // send via WebSocket
};
