function openProfileModal() {
    document.getElementById("profileModal").classList.remove("hidden");
}

function closeProfileModal() {
    document.getElementById("profileModal").classList.add("hidden");
}

function previewProfilePhoto(event) {
    const preview = document.getElementById("profilePhotoPreview");
    const file = event.target.files[0];

    if (!file) return;

    if (file.size > 1024 * 1024) {
        alert("Image must be smaller than 1MB");
        event.target.value = "";
        return;
    }

    // Replace initials div with image if needed
    if (preview.tagName !== "IMG") {
        const img = document.createElement("img");
        img.id = "profilePhotoPreview";
        img.className = "w-full h-full object-cover";
        preview.replaceWith(img);
    }

    document.getElementById("profilePhotoPreview").src =
        URL.createObjectURL(file);
}