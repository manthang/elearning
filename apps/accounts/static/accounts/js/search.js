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
        
        // Provide a fallback for the avatar using your model's logic
        const avatar = u.avatar_url || "/media/profile_photos/default-avatar.png";

        card.innerHTML = `
          <img src="${avatar}" class="w-12 h-12 rounded-full object-cover bg-gray-100 shadow-sm" alt="Avatar" />
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-2">
              <p class="font-bold text-sm text-gray-900 truncate">${u.full_name}</p>
              ${u.enrolled_courses > 0 ? `
                <span class="flex items-center gap-1 px-2 py-0.5 rounded-full bg-purple-50 text-[10px] font-bold text-purple-600 border border-purple-100">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                  ${u.enrolled_courses}
                </span>
              ` : ''}
            </div>
            
            <div class="flex items-center gap-1.5 mt-0.5">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <p class="text-xs text-gray-500 truncate">${u.email}</p>
            </div>

            ${u.location ? `
              <div class="flex items-center gap-1.5 mt-1">
                <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <p class="text-xs text-gray-500 truncate">${u.location}</p>
              </div>
            ` : ""}
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

  // Basic Info
  setEl("profileName", data.full_name || data.username);
  setEl("profileRole", data.role);
  setEl("profileEmail", data.email);
  setEl("profileLocation", data.location);
  setEl("profileJoined", data.joined);
  setEl("profileBio", data.bio);

  // 1. Handle Student Stats (Count only)
  const studentStats = document.getElementById("profileStats");
  if (studentStats) {
    if (typeof data.enrolled_courses === "number") {
      studentStats.classList.remove("hidden");
      setEl("profileCourses", data.enrolled_courses);
    } else {
      studentStats.classList.add("hidden");
    }
  }

  // 2. Handle Teacher Stats (List of courses)
  const teacherStats = document.getElementById("teacherStats");
  const courseListContainer = document.getElementById("teachingCourseList");
  
  if (teacherStats && courseListContainer) {
    if (data.teaching_courses && data.teaching_courses.length > 0) {
      teacherStats.classList.remove("hidden");
      
      // Clear and rebuild the list
      courseListContainer.innerHTML = data.teaching_courses.map(course => `
        <div class="flex items-center gap-2 py-1 px-2 bg-gray-50 rounded-lg border border-gray-100 mb-1">
          <svg class="w-3 h-3 text-blue-500" fill="currentColor" viewBox="0 0 20 20"><path d="M10 12a2 2 0 100-4 2 2 0 000 4z"/><path fill-rule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clip-rule="evenodd"/></svg>
          <span class="text-xs font-medium text-gray-700">${course.title}</span>
        </div>
      `).join('');
    } else {
      teacherStats.classList.add("hidden");
    }
  }

  // Avatar
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