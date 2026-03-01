from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone
from django.db.models import Q, Prefetch, Avg, Count, Exists, OuterRef
from django.contrib.auth import get_user_model
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse

from apps.courses.models import *
from apps.courses.utils import _get_enrolled_courses_data, _get_all_courses_catalog
from ..utils import _get_teacher_profile_data


User = get_user_model()


@login_required
def dashboard_redirect(request):
    """Simply redirects /home/ to the user's personal @username URL."""
    return redirect("accounts:user_profile", username=request.user.username)


def user_profile(request, username):
    # Fetch the user whose profile is being visited
    profile_user = get_object_or_404(User, username=username)

    # PRIVACY CHECK: If it's a student profile and visitor is a guest
    if profile_user.role == 'STUDENT' and not request.user.is_authenticated:
        # Redirect to login and bring them back here after they sign in
        login_url = reverse('accounts:login')
        return redirect(f"{login_url}?next={request.path}")

    # If they passed the check (or it's a teacher profile), continue...
    is_own_profile = (request.user == profile_user) if request.user.is_authenticated else False
    
    tab = request.GET.get("tab", "my_courses")
    show_overdue = request.GET.get("show_overdue") == "1"

    context = {
        "profile_user": profile_user,
        "is_own_profile": is_own_profile,
        "tab": tab,
        "show_overdue": show_overdue,
    }

    # ================= ROLE-BASED ROUTING =================
    if profile_user.role == profile_user.Role.TEACHER:
        # Teacher Logic
        taught_courses, teacher_stats = _get_teacher_profile_data(profile_user, is_own_profile)
        context.update(teacher_stats)  
        context["taught_courses"] = taught_courses
        
        # Deadlines Base Query
        deadlines = Deadline.objects.filter(course__teachings__teacher=profile_user)

    else:
        # Student Logic 
        enrolled_courses, enrolled_course_ids = _get_enrolled_courses_data(profile_user)
        context["enrolled_courses"] = enrolled_courses
        context["enrolled_count"] = len(enrolled_courses)
        
        # Deadlines Base Query
        deadlines = Deadline.objects.filter(course_id__in=enrolled_course_ids)

    # Apply deadline filters (Done once for whoever is logged in)
    if not show_overdue:
        deadlines = deadlines.filter(due_at__gte=timezone.now())
    context["deadlines"] = deadlines.order_by("due_at")[:5]


    # ================= SHARED LOGIC =================
    
    # All Course Catalog (Accessible to both Teachers and Students)
    if is_own_profile and tab == "all_courses":
        
        # Optimize query and attach 'is_enrolled' boolean to every course
        catalog_qs = Course.objects.prefetch_related('teachings__teacher').annotate(
            students_total=Count('enrollments', distinct=True),
            is_enrolled=Exists(
                Enrollment.objects.filter(course=OuterRef('pk'), student=request.user)
            ),
            avg_rating=Avg('feedback__rating'), 
            rating_count=Count('feedback', distinct=True)
        )
        
        # Search Filter
        search_query = request.GET.get('q', '').strip()
        if search_query:
            catalog_qs = catalog_qs.filter(
                Q(title__icontains=search_query) | 
                Q(description__icontains=search_query)
            )
            
        # Category Filter
        category_filter = request.GET.get('category', '').strip()
        if category_filter:
            catalog_qs = catalog_qs.filter(category=category_filter)
            
        catalog_qs = catalog_qs.order_by('-created_at')
        
        # Pagination Setup (12 courses per page)
        paginator = Paginator(catalog_qs, 12)
        page_number = request.GET.get('page')
        
        context.update({
            "all_courses": paginator.get_page(page_number),
            "search_query": search_query,
            "current_category": category_filter,
            "category_choices": Course.CATEGORY_CHOICES,
        })

    # 2. Social Wall
    if tab == "status":
        context["statuses"] = profile_user.status_updates.select_related("author").prefetch_related("liked_by")[:20]

    return render(request, "accounts/profile.html", context)


@login_required
@require_POST
def edit_profile(request):
    user = request.user
    
    # Update text fields
    user.full_name = request.POST.get("full_name", "").strip()
    user.location = request.POST.get("location", "").strip()
    user.bio = request.POST.get("bio", "").strip()

    # Handle explicitly removing the photo
    if request.POST.get("remove_photo") == "1":
        if user.profile_photo:
            # Delete the actual image file from your media folder to save space
            user.profile_photo.delete(save=False) 
        # Clear the database field
        user.profile_photo = None 

    # Handle uploading a new photo
    elif "profile_photo" in request.FILES:
        if user.profile_photo:
            user.profile_photo.delete(save=False) # Clean up the old one first
        user.profile_photo = request.FILES["profile_photo"]

    user.save()
    messages.success(request, "Profile updated successfully!")

    # Safely redirect back to wherever they were
    next_url = request.POST.get("next") or reverse("accounts:user_profile", kwargs={"username": user.username})
    return redirect(next_url)


@login_required
def user_search(request):
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role")

    users = User.objects.all()

    # Filter by role if provided
    if role:
        users = users.filter(role__iexact=role)

    # Filter by search query
    if query:
        users = users.filter(
            Q(full_name__icontains=query) |
            Q(email__icontains=query)
        )

    users = users[:10]

    results = []
    for u in users:
        results.append({
            "id": u.id,
            "username": u.username,
            "name": u.full_name or u.username,
            "email": u.email,
            "location": u.location or "",
            "avatar": u.avatar_url,
        })

    return JsonResponse({"results": results})
