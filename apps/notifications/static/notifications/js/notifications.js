// Function to get the CSRF token from Django's cookies
function getDjangoCSRFToken() {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, 'csrftoken'.length + 1) === ('csrftoken' + '=')) {
                cookieValue = decodeURIComponent(cookie.substring('csrftoken'.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener("DOMContentLoaded", () => {
    fetchUnreadNotifications();
});

// ========================================================
// REAL-TIME WEBSOCKET CONNECTION
// ========================================================
const wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
const notificationSocket = new WebSocket(wsProtocol + window.location.host + '/ws/notifications/');

notificationSocket.onmessage = function(e) {
    let data;
    try { 
        data = JSON.parse(e.data); 
    } catch (err) { 
        console.error("Error parsing websocket message", err);
        return; 
    }

    // When the consumer sends the notification, route it UI function
    if (data.type === "notification") {
        console.log("Live notification received!", data.payload);
        handleRealtimeNotification(data.payload);
    }
};

notificationSocket.onclose = function(e) {
    console.error('Notification WebSocket closed unexpectedly.');
};
// ========================================================

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
        const isRead = notif.is_read;
        const item = document.createElement("a");
        item.href = "javascript:void(0)";
        item.onclick = () => handleNotificationClick(notif.id, notif.link);
        
        // Background: Blue tint if unread, plain white if read
        const bgClass = isRead ? "bg-white hover:bg-gray-50" : "bg-blue-50/40 hover:bg-blue-50/60";
        item.className = `block relative px-4 py-3.5 border-b border-gray-50 transition-colors cursor-pointer group ${bgClass}`;

        // Icons: Same logic as before
        let iconHtml = '';
        if (notif.notification_type === 'ENROLLMENT') {
            iconHtml = `<div class="w-9 h-9 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0 mt-0.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/></svg></div>`;
        } else if (notif.notification_type === 'MATERIAL') {
            iconHtml = `<div class="w-9 h-9 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 mt-0.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>`;
        }
        
        // Dim the icon slightly if the notification is read
        const iconWrapperClass = isRead ? "opacity-50 grayscale" : "";
        
        // Unread Dot
        const unreadDot = isRead ? "" : `<span class="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-600 shadow-[0_0_4px_rgba(37,99,235,0.6)]"></span>`;
        
        // Text Colors
        const baseTextColor = isRead ? "text-gray-400" : "text-gray-600";
        const timeColor = isRead ? "text-gray-400" : "text-blue-500/80";

        item.innerHTML = `
            ${unreadDot}
            <div class="flex items-start gap-3 pl-2 w-full">
                <div class="${iconWrapperClass}">
                    ${iconHtml}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm ${baseTextColor} leading-snug group-hover:text-blue-700 transition-colors">
                        ${formatNotificationText(notif.message, isRead)} 
                    </p>
                    <div class="flex items-center gap-1 mt-1.5">
                        <svg class="w-3 h-3 ${timeColor}" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                        <p class="text-[11px] font-medium ${timeColor} uppercase tracking-wide">${notif.time_ago}</p>
                    </div>
                </div>
                
                <div class="shrink-0 relative opacity-0 group-hover:opacity-100 transition-opacity" onclick="event.stopPropagation();">
                    <button type="button" 
                            onclick="toggleSingleNotifMenu('notif-menu-${notif.id}')" 
                            class="p-1 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-200/50 transition-colors">
                        <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" /></svg>
                    </button>
                    
                    <div id="notif-menu-${notif.id}" class="single-notif-menu hidden absolute right-0 top-8 w-36 bg-white rounded-xl shadow-[0_4px_20px_rgb(0,0,0,0.15)] border border-gray-100 py-1 z-50">
                        ${!isRead 
                            ? `<button type="button" onclick="markSingleNotifRead(${notif.id}, this)" class="w-full text-left px-4 py-2.5 text-xs font-medium text-gray-700 hover:bg-gray-50">Mark as read</button>`
                            : `<button type="button" onclick="markSingleNotifUnread(${notif.id}, this)" class="w-full text-left px-4 py-2.5 text-xs font-medium text-gray-700 hover:bg-gray-50">Mark as unread</button>`
                        }
                        <button type="button" onclick="deleteSingleNotif(${notif.id}, this)" class="w-full text-left px-4 py-2.5 text-xs font-medium text-red-600 hover:bg-red-50">Delete</button>
                    </div>
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


function formatNotificationText(unsafe, isRead) {
    let safe = (unsafe || "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    
    // Unread = Dark black bold. Read = Softer gray bold.
    let boldClass = isRead ? "text-gray-600 font-medium" : "text-gray-900 font-semibold";
    
    return safe.replace(/&lt;b&gt;/g, `<span class="${boldClass}">`)
               .replace(/&lt;\/b&gt;/g, '</span>');
}


window.markAllNotificationsRead = function() {
    fetch('/api/notifications/read-all/', {
        method: 'POST',
        headers: {
            'X-CSRFToken': getDjangoCSRFToken(),
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 1. Hide the red badge on the bell
            const badge = document.getElementById("notificationBadge");
            if (badge) {
                badge.classList.add("hidden");
                badge.textContent = "0";
            }

            // 2. Instantly update all unread items to the "read" state
            const list = document.getElementById("notificationList");
            if (list) {
                // Find all items using the new unread background class
                const unreadItems = list.querySelectorAll(".bg-blue-50\\/40");
                
                unreadItems.forEach(item => {
                    // A. Swap background from blue to white
                    item.classList.remove("bg-blue-50/40", "hover:bg-blue-50/60");
                    item.classList.add("bg-white", "hover:bg-gray-50");
                    
                    // B. Remove the glowing blue dot
                    const dot = item.querySelector("span.bg-blue-600");
                    if (dot) dot.remove();
                    
                    // C. Apply grayscale and opacity to the icon
                    const iconWrapper = item.querySelector(".flex.items-start > div:first-child");
                    if (iconWrapper) {
                        iconWrapper.classList.add("opacity-50", "grayscale");
                    }
                    
                    // D. Dim the main message text
                    const messageText = item.querySelector("p.text-sm");
                    if (messageText) {
                        messageText.classList.remove("text-gray-600");
                        messageText.classList.add("text-gray-400");
                        
                        // Dim the bolded keywords inside the message
                        const bTags = messageText.querySelectorAll("span.text-gray-900");
                        bTags.forEach(b => {
                            b.classList.remove("text-gray-900", "font-semibold");
                            b.classList.add("text-gray-600", "font-medium");
                        });
                    }
                    
                    // E. Dim the timestamp and clock icon
                    const timeContainer = item.querySelector(".mt-1\\.5");
                    if (timeContainer) {
                        const timeElements = timeContainer.querySelectorAll(".text-blue-500\\/80");
                        timeElements.forEach(el => {
                            el.classList.remove("text-blue-500/80");
                            el.classList.add("text-gray-400");
                        });
                    }
                });
            }
        }
    })
    .catch(error => console.error("Error marking all as read:", error));
};


window.handleRealtimeNotification = function(notif) {
    // 1. Un-hide and Increment the Red Badge
    const badge = document.getElementById("notificationBadge");
    if (badge) {
        badge.classList.remove("hidden");
        let currentCount = parseInt(badge.textContent) || 0;
        badge.textContent = currentCount + 1;
    }

    // 2. Locate the Dropdown List
    const list = document.getElementById("notificationList");
    if (!list) return;

    // Remove the "Loading..." spinner if this is the very first notification
    const loadingSpinner = list.querySelector(".animate-spin");
    if (loadingSpinner) list.innerHTML = "";

    // 3. Build the new HTML Element
    const item = document.createElement("a");
    item.href = "javascript:void(0)";
    item.onclick = () => handleNotificationClick(notif.id, notif.link);
    
    // Apply the "Unread" styling (blue background)
    item.className = "block relative px-4 py-3.5 border-b border-gray-50 transition-colors cursor-pointer group bg-blue-50/40 hover:bg-blue-50/60";

    // Set the correct Icon
    let iconHtml = '';
    if (notif.notification_type === 'ENROLLMENT') {
        iconHtml = `<div class="w-9 h-9 rounded-full bg-green-100 text-green-600 flex items-center justify-center shrink-0 mt-0.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"/></svg></div>`;
    } else if (notif.notification_type === 'MATERIAL') {
        iconHtml = `<div class="w-9 h-9 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center shrink-0 mt-0.5"><svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg></div>`;
    }

    const unreadDot = `<span class="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-600 shadow-[0_0_4px_rgba(37,99,235,0.6)]"></span>`;

    item.innerHTML = `
        ${unreadDot}
        <div class="flex items-start gap-3 pl-2 w-full"> <div>${iconHtml}</div>
            <div class="flex-1 min-w-0">
                <p class="text-sm text-gray-600 leading-snug group-hover:text-blue-700 transition-colors">
                    ${formatNotificationText(notif.message, false)} 
                </p>
                <div class="flex items-center gap-1 mt-1.5">
                    <svg class="w-3 h-3 text-blue-500/80" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                    <p class="text-[11px] font-medium text-blue-500/80 uppercase tracking-wide">${notif.time_ago}</p>
                </div>
            </div>
            
            <div class="shrink-0 relative opacity-0 group-hover:opacity-100 transition-opacity" onclick="event.stopPropagation();">
                <button type="button" 
                        onclick="toggleSingleNotifMenu('notif-menu-${notif.id}')" 
                        class="p-1 rounded-md text-gray-400 hover:text-gray-700 hover:bg-gray-200/50 transition-colors">
                    <svg class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z" /></svg>
                </button>
                
                <div id="notif-menu-${notif.id}" class="single-notif-menu hidden absolute right-0 top-8 w-36 bg-white rounded-xl shadow-[0_4px_20px_rgb(0,0,0,0.15)] border border-gray-100 py-1 z-50">
                    <button type="button" onclick="markSingleNotifRead(${notif.id}, this)" class="w-full text-left px-4 py-2.5 text-xs font-medium text-gray-700 hover:bg-gray-50">Mark as read</button>
                    <button type="button" onclick="deleteSingleNotif(${notif.id}, this)" class="w-full text-left px-4 py-2.5 text-xs font-medium text-red-600 hover:bg-red-50">Delete</button>
                </div>
            </div>
        </div>
    `;
    
    // 4. Prepend puts the newest notification at the TOP of the list
    list.prepend(item);
};


// Toggle the individual notification menu
window.toggleSingleNotifMenu = function(menuId) {
    // First, close any other open menus
    document.querySelectorAll('.single-notif-menu').forEach(menu => {
        if (menu.id !== menuId) menu.classList.add('hidden');
    });
    
    // Toggle the target menu
    const menu = document.getElementById(menuId);
    if (menu) menu.classList.toggle('hidden');
};

// Delete a single notification
window.deleteSingleNotif = function(notifId, btnElement) {
    fetch(`/api/notifications/${notifId}/delete/`, {
        method: 'DELETE',
        headers: {
            'X-CSRFToken': getDjangoCSRFToken(),
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            // Find the main <a> tag (parent of the menu) and remove it smoothly
            const item = btnElement.closest('a');
            
            // Check if it was unread to decrement the badge
            if (item.classList.contains('bg-blue-50/40')) {
                decrementBadge();
            }
            
            // Remove from DOM
            item.remove();
        }
    });
};

// UPDATE: Modify your existing 'markSingleNotifRead' to toggle the button instead of deleting it
window.markSingleNotifRead = function(notifId, btnElement) {
    fetch(`/api/notifications/${notifId}/read/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getDjangoCSRFToken(),
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            const item = btnElement.closest('a');
            
            item.classList.remove("bg-blue-50/40", "hover:bg-blue-50/60");
            item.classList.add("bg-white", "hover:bg-gray-50");
            
            const dot = item.querySelector("span.bg-blue-600");
            if (dot) dot.remove();
            
            const iconWrapper = item.querySelector(".flex.items-start > div:first-child");
            if (iconWrapper) iconWrapper.classList.add("opacity-50", "grayscale");
            
            const messageText = item.querySelector("p.text-sm");
            if (messageText) {
                messageText.classList.remove("text-gray-600");
                messageText.classList.add("text-gray-400");
                const bTags = messageText.querySelectorAll("span.text-gray-900");
                bTags.forEach(b => {
                    b.classList.remove("text-gray-900", "font-semibold");
                    b.classList.add("text-gray-600", "font-medium");
                });
            }
            
            // THIS IS THE CHANGE: Morph the button into "Mark as unread"
            btnElement.textContent = "Mark as unread";
            btnElement.setAttribute("onclick", `markSingleNotifUnread(${notifId}, this)`);
            
            decrementBadge();
        }
    });
};

// Helper to lower the red badge number
function decrementBadge() {
    const badge = document.getElementById("notificationBadge");
    if (badge && !badge.classList.contains("hidden")) {
        let currentCount = parseInt(badge.textContent) || 0;
        if (currentCount > 1) {
            badge.textContent = currentCount - 1;
        } else {
            badge.classList.add("hidden");
            badge.textContent = "0";
        }
    }
}

// Ensure clicking anywhere else closes the mini-menus
document.addEventListener("click", function () {
    document.querySelectorAll('.single-notif-menu').forEach(menu => {
        menu.classList.add('hidden');
    });
});

// NEW: Mark a notification as Unread
window.markSingleNotifUnread = function(notifId, btnElement) {
    fetch(`/api/notifications/${notifId}/unread/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getDjangoCSRFToken(),
            'Content-Type': 'application/json'
        }
    }).then(response => response.json())
    .then(data => {
        if (data.success) {
            const item = btnElement.closest('a');
            
            // 1. Swap background back to unread blue
            item.classList.remove("bg-white", "hover:bg-gray-50");
            item.classList.add("bg-blue-50/40", "hover:bg-blue-50/60");
            
            // 2. Add the glowing blue dot back
            if (!item.querySelector("span.bg-blue-600")) {
                const dotHtml = `<span class="absolute left-1.5 top-1/2 -translate-y-1/2 w-1.5 h-1.5 rounded-full bg-blue-600 shadow-[0_0_4px_rgba(37,99,235,0.6)]"></span>`;
                item.insertAdjacentHTML('afterbegin', dotHtml);
            }
            
            // 3. Remove grayscale from the icon
            const iconWrapper = item.querySelector(".flex.items-start > div:first-child");
            if (iconWrapper) iconWrapper.classList.remove("opacity-50", "grayscale");
            
            // 4. Restore the bold, dark text
            const messageText = item.querySelector("p.text-sm");
            if (messageText) {
                messageText.classList.remove("text-gray-400");
                messageText.classList.add("text-gray-600");
                const bTags = messageText.querySelectorAll("span.text-gray-600.font-medium");
                bTags.forEach(b => {
                    b.classList.remove("text-gray-600", "font-medium");
                    b.classList.add("text-gray-900", "font-semibold");
                });
            }
            
            // 5. Morph the button back into "Mark as read"
            btnElement.textContent = "Mark as read";
            btnElement.setAttribute("onclick", `markSingleNotifRead(${notifId}, this)`);
            
            // 6. Increase the red bell badge
            incrementBadge();
        }
    });
};

// NEW: Helper to increase the red badge
function incrementBadge() {
    const badge = document.getElementById("notificationBadge");
    if (badge) {
        badge.classList.remove("hidden");
        let currentCount = parseInt(badge.textContent) || 0;
        badge.textContent = currentCount + 1;
    }
}