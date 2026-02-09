let currentRole = "student";

function openSearch() {
  document.getElementById("searchModal").classList.remove("hidden");
  document.getElementById("searchInput").value = "";
  document.getElementById("searchResults").innerHTML = "";
  document.getElementById("searchInput").focus();
}

function closeSearch() {
  document.getElementById("searchModal").classList.add("hidden");
}

function setSearchRole(role) {
  currentRole = role;

  document.getElementById("tabStudent").className =
    role === "student"
      ? "flex-1 py-2 rounded-xl bg-blue-600 text-white font-medium"
      : "flex-1 py-2 rounded-xl bg-gray-100 text-gray-600 font-medium";

  document.getElementById("tabTeacher").className =
    role === "teacher"
      ? "flex-1 py-2 rounded-xl bg-blue-600 text-white font-medium"
      : "flex-1 py-2 rounded-xl bg-gray-100 text-gray-600 font-medium";

  searchUsers();
}

function searchUsers() {
  const q = document.getElementById("searchInput").value.trim();
  const container = document.getElementById("searchResults");

  if (!q) {
    container.innerHTML = "";
    return;
  }

  fetch(`/accounts/search/?q=${encodeURIComponent(q)}&role=${currentRole}`)
    .then(res => res.json())
    .then(data => {
      container.innerHTML = "";

      if (data.results.length === 0) {
        container.innerHTML =
          `<p class="text-sm text-gray-400">No results found</p>`;
        return;
      }

      data.results.forEach(u => {
        container.insertAdjacentHTML("beforeend", `
          <div
            onclick="openUserProfile(${u.id})"
            class="border rounded-xl p-4 flex gap-4 hover:bg-gray-50 cursor-pointer"
          >
            <img src="${u.avatar}" class="w-10 h-10 rounded-full object-cover" />
            <div>
              <p class="font-semibold text-sm">${u.name}</p>
              <p class="text-xs text-gray-500">✉ ${u.email}</p>
              <p class="text-xs text-gray-500">📍 ${u.location}</p>
            </div>
          </div>
        `);
      });
    });
}

function openUserProfile(userId) {
  fetch(`/accounts/profile/${userId}/`)
    .then(res => {
      if (!res.ok) throw new Error("Profile not found");
      return res.json();
    })
    .then(data => {
      // switch views
      document.getElementById("searchView").classList.add("hidden");
      document.getElementById("profileView").classList.remove("hidden");

      // fill data
      document.getElementById("profileName").innerText = data.full_name;
      document.getElementById("profileRole").innerText = data.role;
      document.getElementById("profileEmail").innerText = data.email;
      document.getElementById("profileLocation").innerText = data.location || "—";
      document.getElementById("profileJoined").innerText = data.joined;
      document.getElementById("profileBio").innerText = data.bio || "";

      document.getElementById("profileAvatar").src =
        data.avatar || "/static/img/default-avatar.png";

      if (data.enrolled_courses !== null) {
        document.getElementById("profileStats").classList.remove("hidden");
        document.getElementById("profileCourses").innerText =
          data.enrolled_courses;
      } else {
        document.getElementById("profileStats").classList.add("hidden");
      }
    })
    .catch(() => alert("Unable to load profile"));
}

function backToSearch() {
  document.getElementById("profileView").classList.add("hidden");
  document.getElementById("searchView").classList.remove("hidden");
}
