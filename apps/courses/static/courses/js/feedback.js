function openFeedbackModal(courseTitle, actionUrl, rating, comment) {
    // show modal
    document.getElementById("feedbackModal").classList.remove("hidden");
    document.getElementById("feedbackCourseTitle").innerText = courseTitle;
    document.getElementById("feedbackForm").action = actionUrl;

    // reset state
    document.getElementById("ratingInput").value = "";
    document.getElementById("submitFeedbackBtn").disabled = true;

    // reset stars
    for (let i = 1; i <= 5; i++) {
      document.getElementById("star" + i).style.color = "#d1d5db";
    }

    // prefill comment
    document.querySelector(
      "#feedbackForm textarea[name='comment']"
    ).value = comment || "";

    // prefill rating ONLY through setRating
    if (rating && rating > 0) {
      setRating(rating);
    }
}

function closeFeedbackModal() {
    document.getElementById("feedbackModal").classList.add("hidden");
}

function setRating(value) {
    document.getElementById("ratingInput").value = value;

    for (let i = 1; i <= 5; i++) {
      document.getElementById("star" + i).style.color =
        i <= value ? "#2563eb" : "#d1d5db";
    }

    // enable submit ONLY here
    document.getElementById("submitFeedbackBtn").disabled = false;
}