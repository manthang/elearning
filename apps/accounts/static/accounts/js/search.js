/* =========================
   STATE VARIABLES
========================= */
let currentRole = "student";
let selectedUserId = null;
let searchTimeout = null;

/* =========================
   SEARCH MODAL CONTROL
========================= */

function openSearch() {
  const modal = document.getElementById("searchModal");
  if (modal) {
    modal.classList.remove("hidden");
    showSearchView();
    document.getElementById("searchInput").value = "";
    document.getElementById("searchResults").innerHTML = "";
    // Delay focus slightly to ensure the transition doesn't block it
    setTimeout(() => document.getElementById("searchInput").focus(), 150);
  }
}

function closeSearch() {
  document.getElementById("searchModal").classList.add("hidden");
  selectedUserId = null;
}

/* =========================
   ROLE TABS
========================= */

function setSearchRole(role) {
  currentRole = role;

  // Base classes ensure buttons never change size or alignment when clicked
  const base = "flex-1 flex items-center justify-center gap-2 h-11 rounded-xl font-bold text-sm transition shadow-sm ";
  const active = base + "bg-blue-600 text-white";
  const inactive = base + "bg-gray-50 text-gray-500 hover:bg-gray-100";

  const tabStudent = document.getElementById("tabStudent");
  const tabTeacher = document.getElementById("tabTeacher");

  if (tabStudent && tabTeacher) {
    tabStudent.className = role === "student" ? active : inactive;
    tabTeacher.className = role === "teacher" ? active : inactive;
  }

  searchUsers();
}

/* =========================
   SEARCH USERS (Debounced)
========================= */

function searchUsers() {
  const q = document.getElementById("searchInput").value.trim();
  const container = document.getElementById("searchResults");

  if (searchTimeout) clearTimeout(searchTimeout);

  if (!q) {
    container.innerHTML = "";
    return;
  }

  // Visual feedback while typing
  container.innerHTML = `<p class="text-sm text-gray-400 text-center py-4">Searching...</p>`;

  searchTimeout = setTimeout(() => {
    fetch(`/users/search/?q=${encodeURIComponent(q)}&role=${currentRole}`, {
      headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(res => {
      if (!res.ok) throw new Error("Search request failed");
      return res.json();
    })
    .then(data => {
      container.innerHTML = "";

      if (!data.results || data.results.length === 0) {
        container.innerHTML = `<p class="text-sm text-gray-400 text-center py-4">No ${currentRole}s found</p>`;
        return;
      }

      data.results.forEach(u => {
        const card = document.createElement("div");
        card.className = "border border-gray-100 rounded-xl p-4 flex gap-4 hover:bg-gray-50 cursor-pointer transition shadow-sm bg-white";
        
        // Use the avatar_url property from your model
        const avatar = u.avatar_url || "/media/profile_photos/default-avatar.png";

        card.innerHTML = `
          <img src="${avatar}" class="w-12 h-12 rounded-full object-cover bg-gray-100" />
          <div class="flex-1 min-w-0">
            <p class="font-bold text-sm text-gray-900 truncate">${u.full_name}</p>
            <p class="text-xs text-gray-500 truncate">✉ ${u.email}</p>
            ${u.location ? `<p class="text-xs text-gray-500 mt-1">📍 ${u.location}</p>` : ""}
          </div>
        `;

        // Instead of just passing the username, pass the whole object 'u'
        card.addEventListener("click", () => openUserProfile(u.username, u));
        container.appendChild(card);
      });
    })
    .catch(err => {
      console.error(err);
      container.innerHTML = `<p class="text-sm text-red-400 text-center py-4">Search error. Try again.</p>`;
    });
  }, 300);
}

/* =========================
   PROFILE VIEW
========================= */
function openUserProfile(userName, cachedData = null) {
  // 1. If we have cachedData from the search result, populate the UI immediately
  if (cachedData) {
    populateProfileUI(cachedData);
    showProfileView(); //
  }

  // 2. Fetch fresh data from the API anyway to ensure bio/joined date are current
  fetch(`/api/users/${encodeURIComponent(userName)}/?format=json`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(res => res.json())
    .then(data => {
      populateProfileUI(data); // Refresh with the latest data
      if (!cachedData) showProfileView();
    })
    .catch(err => {
      if (!cachedData) alert("Unable to load profile.");
    });
}

function populateProfileUI(data) {
  selectedUserId = data.id;
  
  const setEl = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.innerText = val || "—";
  };

  setEl("profileName", data.full_name || data.username);
  setEl("profileRole", data.role);
  setEl("profileEmail", data.email);
  setEl("profileLocation", data.location);
  setEl("profileJoined", data.joined);
  setEl("profileBio", data.bio);

  const avatarImg = document.getElementById("profileAvatar");
  if (avatarImg) {
    avatarImg.src = data.avatar_url || "/media/profile_photos/default-avatar.png";
  }
}

function openMessengerWithUser() {
  if (!selectedUserId) return;
  const userId = selectedUserId;

  closeSearch();

  fetch(`/chat/start/${userId}/`, {
    headers: { 'X-Requested-With': 'XMLHttpRequest' }
  })
    .then(res => res.json())
    .then(data => {
      if (window.openMessenger) {
        window.openMessenger(data.conversation_id);
      }
    })
    .catch(err => console.error("Chat start failed:", err));
}

/* =========================
   VIEW SWITCHING (Tailwind Safe)
========================= */

function showSearchView() {
  const sv = document.getElementById("searchView");
  const pv = document.getElementById("profileView");
  
  if (pv) { pv.classList.add("hidden"); pv.classList.remove("flex"); }
  if (sv) { sv.classList.remove("hidden"); sv.classList.add("flex"); }
}

function showProfileView() {
  const sv = document.getElementById("searchView");
  const pv = document.getElementById("profileView");

  if (sv) { sv.classList.add("hidden"); sv.classList.remove("flex"); }
  if (pv) { pv.classList.remove("hidden"); pv.classList.add("flex"); }
}

function backToSearch() {
  selectedUserId = null;
  showSearchView();
}