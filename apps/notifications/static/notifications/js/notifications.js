document.addEventListener("DOMContentLoaded", () => {
    fetchUnreadNotifications();
});

window.toggleNotificationMenu = function() {
    const menu = document.getElementById("notificationMenu");
    if (!menu) return;
    menu.classList.toggle("hidden");
    menu.classList.toggle("flex");
};

// Auto-close dropdown when clicking outside
document.addEventListener("click", (e) => {
    const menu = document.getElementById("notificationMenu");
    const btn = document.getElementById("notificationBtn");
    if (menu && !menu.classList.contains("hidden")) {
        if (!menu.contains(e.target) && !btn.contains(e.target)) {
            menu.classList.add("hidden");
            menu.classList.remove("flex");
        }
    }
});

function fetchUnreadNotifications() {
    fetch('/api/notifications/')
        .then(response => response.json())
        .then(data => {
            updateNotificationUI(data.count, data.notifications);
        })
        .catch(error => console.error('Error fetching notifications:', error));
}

function updateNotificationUI(count, notifications) {
    const badge = document.getElementById("notificationBadge");
    const list = document.getElementById("notificationList");

    // 1. Update Badge
    if (count > 0) {
        badge.textContent = count > 9 ? '9+' : count;
        badge.classList.remove("hidden");
    } else {
        badge.classList.add("hidden");
    }

    // 2. Render List
    if (notifications.length === 0) {
        list.innerHTML = `<div class="p-4 text-center text-sm text-gray-500">No new notifications</div>`;
        return;
    }

    list.innerHTML = "";
    const fragment = document.createDocumentFragment();

    notifications.forEach(notif => {
        const item = document.createElement("a");
        item.href = "javascript:void(0)";
        item.className = "block px-4 py-3 border-b border-gray-50 hover:bg-blue-50/50 transition cursor-pointer";
        item.onclick = () => handleNotificationClick(notif.id, notif.link);

        // Icon logic based on notification type
        let iconHtml = '';
        if (notif.notification_type === 'ENROLLMENT') {
            iconHtml = `<div class="h-8 w-8 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"/></svg></div>`;
        } else if (notif.notification_type === 'MATERIAL') {
            iconHtml = `<div class="h-8 w-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>`;
        }

        item.innerHTML = `
            <div class="flex items-start gap-3">
                ${iconHtml}
                <div class="flex-1 min-w-0">
                    <p class="text-sm text-gray-800 leading-snug">${escapeHtml(notif.message)}</p>
                    <p class="text-xs text-gray-400 mt-1">${notif.time_ago}</p>
                </div>
            </div>
        `;
        fragment.appendChild(item);
    });

    list.appendChild(fragment);
}

function handleNotificationClick(notifId, redirectLink) {
    // Call API to mark as read
    fetch(`/api/notifications/${notifId}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getDjangoCSRFToken(),
            'Content-Type': 'application/json'
        }
    }).then(() => {
        // Redirect the user to the relevant page
        if (redirectLink) {
            window.location.href = redirectLink;
        } else {
            // If no link, just refresh the list
            fetchUnreadNotifications();
        }
    });
}

// Utility to escape HTML to prevent XSS
function escapeHtml(unsafe) {
    return (unsafe || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
}