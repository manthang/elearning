from django.db.models import Prefetch, Avg, Count, Exists, OuterRef, Q, Value, BooleanField
from .models import *


def _get_annotated_courses_queryset(user=None, search_query=None):
    # 1. Base Annotations (Static stats)
    queryset = Course.objects.annotate(
        students_total=Count("enrollments", distinct=True),
        materials_total=Count("materials", distinct=True),
        avg_rating=Avg("feedback__rating"),
        rating_count=Count("feedback", distinct=True)
    )

    # 2. Search Logic
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) | 
            Q(description__icontains=search_query)
        ).distinct() # Prevent duplicates if searching via M2M joins

    # 3. Relationship Annotations (Safe for AnonymousUsers)
    if user and user.is_authenticated:
        # Use string comparisons or hasattr to avoid 'AnonymousUser' attribute errors
        user_role = getattr(user, 'role', None)
        
        queryset = queryset.annotate(
            is_owner=Exists(
                Course.objects.filter(pk=OuterRef('pk'), teachings__teacher=user)
            ) if user_role == 'TEACHER' else Value(False, output_field=BooleanField()),
            
            is_enrolled=Exists(
                Enrollment.objects.filter(course=OuterRef('pk'), student=user)
            )
        )
    else:
        # For guests, set these to False so templates don't crash
        queryset = queryset.annotate(
            is_owner=Value(False, output_field=BooleanField()),
            is_enrolled=Value(False, output_field=BooleanField())
        )
    
    return queryset.order_by("-updated_at", "-created_at", "title")


def _get_enrolled_courses_data(user):
    """Fetches courses a specific user is enrolled in, with teachers and progress."""
    enrollments = Enrollment.objects.filter(student=user)
    progress_map = {e.course_id: e.progress for e in enrollments}
    enrolled_course_ids = set(progress_map.keys())

    teachers_prefetch = Prefetch(
        "teachings",
        queryset=Teaching.objects.select_related("teacher"),
        to_attr="course_teachings"
    )
    
    user_feedback_prefetch = Prefetch(
        "feedback",
        queryset=CourseFeedback.objects.filter(student=user),
        to_attr="user_feedback"
    )

    # Fetch only the courses this user is enrolled in
    courses_qs = Course.objects.filter(id__in=enrolled_course_ids).prefetch_related(
        teachers_prefetch, user_feedback_prefetch
    )

    enrolled_courses = []
    for course in courses_qs:
        course.progress = progress_map.get(course.id, 0)
        course.teachers = [t.teacher for t in course.course_teachings]
        
        feedback = course.user_feedback[0] if course.user_feedback else None
        course.feedback_rating = feedback.rating if feedback else 0
        course.feedback_comment = feedback.comment if feedback else ""
        
        enrolled_courses.append(course)

    return enrolled_courses, enrolled_course_ids


def _get_all_courses_catalog(enrolled_course_ids):
    """Fetches the global course catalog with average ratings."""
    teachers_prefetch = Prefetch("teachings", queryset=Teaching.objects.select_related("teacher"), to_attr="course_teachings")
    
    catalog_qs = Course.objects.annotate(
        avg_rating=Avg("feedback__rating"),
        rating_count=Count("feedback")
    ).prefetch_related(teachers_prefetch)

    all_courses = []
    for course in catalog_qs:
        course.is_enrolled = course.id in enrolled_course_ids
        course.teachers = [t.teacher for t in course.course_teachings]
        all_courses.append(course)
        
    return all_courses


def _get_course_feedback_data(course):
    """
    Fetches reviews and calculates all rating statistics for a course.
    Returns a dictionary to be used in views or APIs.
    """
    # Fetch the QuerySet of reviews
    reviews = CourseFeedback.objects.filter(course=course).select_related('student').order_by('-created_at')
    
    # Basic Stats
    total_reviews = reviews.count()
    avg_rating_val = reviews.aggregate(a=Avg('rating'))['a'] or 0
    avg_rating = round(avg_rating_val, 1)

    # Calculate the exact star breakdown (round to nearest 0.5)
    nearest_half = round(avg_rating * 2) / 2
    star_display = []
    
    for i in range(1, 6):
        if nearest_half >= i:
            star_display.append('full')
        elif nearest_half >= i - 0.5:
            star_display.append('half')
        else:
            star_display.append('empty')

    # Rating Distribution (1 to 5 stars)
    counts = dict(reviews.values_list('rating').annotate(c=Count('id')))
    rating_stats = []
    
    for star in range(5, 0, -1):
        count = counts.get(star, 0)
        percent = round((count / total_reviews * 100) if total_reviews > 0 else 0)
        rating_stats.append({
            'stars': star,
            'percent': percent,
            'count': count
        })

    return {
        'reviews': reviews,
        'total_reviews': total_reviews,
        'avg_rating': avg_rating,
        'star_display': star_display,
        'rating_stats': rating_stats,
    }
