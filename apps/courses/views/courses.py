import re
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction, IntegrityError
from django.db.models import Count, Sum, Avg, Q, F
from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from ..models import *
from ..forms import *
from ..utils import _get_course_feedback_data, _get_annotated_courses_queryset


# =========================
# Create Course
# =========================
@login_required
def course_create(request):
    # SAFELY check the role without triggering an attribute error on custom User models
    if getattr(request.user, 'role', '') != 'TEACHER':
        return HttpResponseForbidden("Teachers only")

    COURSE_ID_RE = re.compile(r"^[A-Z0-9_-]+$")

    if request.method == "POST":
        # Capture the page the user submitted the form from. 
        # Fallback to teacher_home if the browser blocks the referer header.
        next_url = request.META.get('HTTP_REFERER') or reverse("core:home")

        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        course_id_input = (request.POST.get("course_id") or "").strip().upper()

        category = (request.POST.get("category") or "").strip()
        duration = (request.POST.get("duration") or "").strip()

        # Validate max_students properly
        max_students_raw = (request.POST.get("max_students") or "").strip()
        max_students = None
        if max_students_raw:
            try:
                max_students = int(max_students_raw)
                if max_students <= 0:
                    messages.error(request, "Max students must be a positive number.")
                    return redirect(next_url)
            except ValueError:
                messages.error(request, "Max students must be a number.")
                return redirect(next_url)

        if not title:
            messages.error(request, "Course title is required.")
            return redirect(next_url)

        # Validate category strictly
        valid_categories = {c[0] for c in Course.CATEGORY_CHOICES}
        if not category:
            category = Course.CATEGORY_GENERAL # Make sure CATEGORY_GENERAL exists on your model
        elif category not in valid_categories:
            messages.error(request, "Invalid category selected.")
            return redirect(next_url)

        # Validate course_id ONLY if provided
        if course_id_input:
            if len(course_id_input) > 20:
                messages.error(request, "Course ID must be 20 characters or fewer.")
                return redirect(next_url)

            if not COURSE_ID_RE.match(course_id_input):
                messages.error(request, "Course ID can only contain A–Z, 0–9, -, _")
                return redirect(next_url)

            if Course.objects.filter(course_id=course_id_input).exists():
                messages.error(request, "Course ID already exists.")
                return redirect(next_url)

        files = request.FILES.getlist("materials")

        # Atomic transaction ensures we don't create a course if the materials fail to upload
        with transaction.atomic():
            course = Course.objects.create(
                course_id=course_id_input or None,
                title=title,
                description=description,
                category=category,
                duration=duration,
                max_students=max_students,
            )

            Teaching.objects.create(
                teacher=request.user,
                course=course
            )

            for f in files:
                CourseMaterial.objects.create(
                    course=course,
                    file=f,
                    original_name=getattr(f, "name", "") or "",
                    uploaded_by=request.user
                )

        messages.success(request, "Course created successfully.")
        return redirect(next_url)

    # If someone visits /course_create directly via GET, provide the standalone page
    return render(request, "courses/course_create.html", {
        "category_choices": Course.CATEGORY_CHOICES
    })

# =========================
# Edit Course
# =========================
@login_required
@require_POST
def course_edit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)

    # Determine where to send the user after processing
    # Fallback to the course detail page if no 'next' parameter is provided
    fallback_url = redirect("courses:course_detail", course_id=course.id)
    next_url = request.POST.get("next")
    redirect_target = redirect(next_url) if next_url else fallback_url

    # Permission Check
    is_teacher = Teaching.objects.filter(course=course, teacher=request.user).exists()
    if not is_teacher:
        messages.error(request, "You don't have permission to edit this course.")
        return redirect_target

    # Extract core fields (Notice we ignore course_id as it shouldn't change)
    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()
    category = (request.POST.get("category") or "").strip()

    # Validation
    if not title:
        messages.error(request, "Course title is required.")
        return redirect_target

    valid_categories = {k for k, _ in Course.CATEGORY_CHOICES}
    if category not in valid_categories:
        messages.error(request, "Invalid category selected.")
        return redirect_target

    # Apply Updates
    course.title = title
    course.description = description
    course.category = category
    course.duration = (request.POST.get("duration") or "").strip() or None

    max_students_raw = (request.POST.get("max_students") or "").strip()
    course.max_students = int(max_students_raw) if max_students_raw.isdigit() else None

    #Save
    try:
        course.save()
        messages.success(request, "Course updated successfully.")
    except Exception as e:
        messages.error(request, f"An error occurred while saving: {str(e)}")

    return redirect_target


# =========================
# Course Detail
# =========================
def course_detail(request, course_id: int):
    course = get_object_or_404(Course, id=course_id)

    # Initialize flags with safe defaults
    is_teacher_view = False
    is_enrolled = False

    # --- COMMON DATA (Needed for Permissions and the Top Header) ---
    is_enrolled = False
    user_feedback = None

    # ONLY check roles and enrollments if the user is logged in
    if request.user.is_authenticated:
        # Check if the user is a teacher AND if they teach this specific course
        # Note: Use 'role' or 'Role' depending on your model's field name
        if hasattr(request.user, 'role') and request.user.role == 'TEACHER':
            is_teacher_view = course.teachings.filter(teacher=request.user).exists()
        
        # If they aren't the teacher, check if they are a student enrolled in it and submitted feedback
        if not is_teacher_view:
            is_enrolled = course.enrollments.filter(student=request.user).exists()
            # Fetch their existing feedback if they have one
            user_feedback = CourseFeedback.objects.filter(student=request.user, course=course).first()

    # Which tab are we on? (Defaults to 'overview')
    current_tab = request.GET.get("tab", "overview")

    # If users aren't authorized, force the tab to 'overview' no matter what the URL says.
    protected_tabs = ['materials', 'deadlines', 'students']
    if current_tab in protected_tabs:
        if not (is_enrolled or is_teacher_view):
            current_tab = 'overview'

    # Try to get the previous URL; if it doesn't exist, fallback to home
    dashboard_url = reverse("core:home") or request.META.get('HTTP_REFERER')

    # Fetch all feedback data
    feedback_data = _get_course_feedback_data(course)

    # --- COMMON DATA (Always passed for the Header) ---
    enrollment_count = Enrollment.objects.filter(course=course).count()
    instructor = Teaching.objects.filter(course=course).select_related("teacher").first()

    context = {
        "course": course,
        "current_tab": current_tab,
        "dashboard_url": dashboard_url,
        "is_teacher_view": is_teacher_view,
        "instructor_user": instructor.teacher if instructor else None,
        "is_enrolled": is_enrolled,
        "enrollment_count": enrollment_count,
        "total_reviews": feedback_data['total_reviews'],
        "avg_rating": feedback_data['avg_rating'],
        "star_display": feedback_data['star_display'],
        "user_feedback": user_feedback,
        'category_choices': Course.CATEGORY_CHOICES,
    }

    # --- CONDITIONAL DATA (Only runs what is needed!) ---
    
    if current_tab == "overview":
        # Maybe fetch course syllabus or recent announcements here
        pass

    elif current_tab == "students" and is_teacher_view:
        # Only fetch the heavy student list and calculate progress if on this tab
        enrollments = Enrollment.objects.filter(course=course).select_related("student").order_by("-id")
        avg_progress = enrollments.aggregate(a=Avg("progress"))["a"] or 0
        
        context["enrollments"] = enrollments
        context["avg_progress"] = int(round(avg_progress))

    elif current_tab == "materials":
        # Only fetch files if on the materials tab
        context["materials"] = CourseMaterial.objects.filter(course=course).order_by("-uploaded_at")

    elif current_tab == "deadlines":
        # Only fetch deadlines if on the deadlines tab
        context["deadlines"] = Deadline.objects.filter(course=course).order_by("due_at")

    elif current_tab == "feedback":
        # Get the full base queryset
        reviews = feedback_data['reviews']
        
        # Grab the URL parameters from the submitted form
        search_query = request.GET.get('search', '').strip()
        rating_filter = request.GET.get('rating')

        # Filter by Search Text
        if search_query:
            reviews = reviews.filter(comment__icontains=search_query)
            
        # Filter by Exact Star Rating
        if rating_filter and rating_filter.isdigit():
            reviews = reviews.filter(rating=int(rating_filter))

        # Pass the newly filtered reviews to the template
        context["reviews"] = reviews
        context["rating_stats"] = feedback_data['rating_stats']

    # Render the single main shell
    return render(request, "courses/course_detail/main.html", context)


# =========================
# Enroll Course
# =========================
@login_required
def course_enroll(request, course_id):
    if request.user.role != request.user.Role.STUDENT:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    # enforce max_students if set
    if course.max_students is not None:
        current = Enrollment.objects.filter(course=course).count()
        if current >= course.max_students:
            messages.error(request, "This course is full.")
            return redirect("courses:student_home")


    # 🔒 Course must have at least one teacher
    if not Teaching.objects.filter(course=course).exists():
        return HttpResponseForbidden(
            "This course is not yet available for enrollment."
        )

    Enrollment.objects.get_or_create(
        student=request.user,
        course=course
    )

    return redirect(f"{reverse('courses:course_detail', args=[course.id])}?tab=overview")


# =========================
# Course Feedback
# =========================
def course_feedback(request, course_id):
    # Security Check
    if not request.user.is_student:
        return HttpResponseForbidden("Students only")

    course = get_object_or_404(Course, id=course_id)

    # Enrollment Check
    is_enrolled = Enrollment.objects.filter(student=request.user, course=course).exists()
    if not is_enrolled:
        return HttpResponseForbidden("You must be enrolled to leave feedback.")

    # Redirect back to the originating page (dashboard or detail view) after saving
    # Priority: 1. 'next' hidden input, 2. Referer header, 3. Default dashboard
    next_url = request.POST.get("next") or request.META.get('HTTP_REFERER')
    
    # Security: Ensure the URL is safe and internal
    if not next_url or not url_has_allowed_host_and_scheme(
        url=next_url, 
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        next_url = reverse("courses:student_home")

    # Handle Form
    existing = CourseFeedback.objects.filter(course=course, student=request.user).first()
    form = CourseFeedbackForm(request.POST, instance=existing)

    if not form.is_valid():
        # Capture specific errors if necessary
        error_msg = form.errors.as_text() if form.errors else "Please provide a valid rating (1–5)."
        messages.error(request, error_msg)
        return redirect(next_url)

    # Save Data
    feedback = form.save(commit=False)
    feedback.course = course
    feedback.student = request.user
    feedback.save()

    messages.success(request, "Feedback submitted successfully!")
    return redirect(next_url)


# =========================
# Course Search
# =========================
def course_search(request):
    # 1. Get query parameters
    search_query = request.GET.get('q', '')
    role_filter = request.GET.get('role', None) # Optional: filter by role
    
    # 2. Fetch the data using our centralized helper
    queryset = _get_annotated_courses_queryset(
        user=request.user, 
        search_query=search_query
    )
    
    # 3. Detect if it's an API request
    # Checks for 'application/json' in headers or a '?format=json' param
    is_api = (
        request.headers.get('Accept') == 'application/json' or 
        request.GET.get('format') == 'json'
    )

    if is_api:
        # Return JSON for API/Frontend JS
        data = list(queryset.values(
            'id', 'title', 'avg_rating', 'rating_count', 'students_total'
        ))
        return JsonResponse({'results': data}, safe=False)

    # Return HTML for standard page reloads
    context = {
        'all_courses': queryset,
        'search_query': search_query,
    }

    # Redirect back to the profile page, specifically the all_courses tab
    # We use a dummy or the current user's profile
    target_username = request.user.username if request.user.is_authenticated else "catalog" 
    
    url = reverse('accounts:user_profile', kwargs={'username': target_username})

    return redirect(f"{url}?tab=all_courses&q={search_query}")