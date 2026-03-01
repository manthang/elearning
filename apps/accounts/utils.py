from django.db.models import Avg, Count, Sum
from apps.courses.models import *


def _get_teacher_profile_data(teacher, is_own_profile):
    """Fetches teacher courses, and optionally private stats if it's their own dashboard."""
    
    # Base Query (Visible to everyone)
    my_courses = (
        Course.objects
        .filter(teachings__teacher=teacher)
        .annotate(
            students_total=Count("enrollments", distinct=True),
            materials_total=Count("materials", distinct=True),
            course_avg_rating=Avg("feedback__rating"),
            course_rating_count=Count("feedback", distinct=True)
        )
        .order_by("-updated_at", "-created_at", "title")
        .distinct()
    )

    stats = {}

    # Strictly private to the owner
    if is_own_profile:
        courses_created = my_courses.count()
        
        total_enrolled = Enrollment.objects.filter(course__teachings__teacher=teacher).count()
        
        total_students = (
            Enrollment.objects
            .filter(course__teachings__teacher=teacher)
            .values("student_id")
            .distinct()
            .count()
        )

        rating_data = CourseFeedback.objects.filter(
            course__teachings__teacher=teacher
        ).aggregate(
            global_avg=Avg('rating'),
            total_reviews=Count('id')
        )
        
        total_materials = CourseMaterial.objects.filter(course__teachings__teacher=teacher).count()

        # Capacity logic
        capped_qs = my_courses.filter(max_students__isnull=False)
        capacity_total = capped_qs.aggregate(total=Sum("max_students"))["total"] or 0
        capped_enrolled = Enrollment.objects.filter(
            course__teachings__teacher=teacher, 
            course__max_students__isnull=False
        ).count()

        stats = {
            "courses_created": courses_created,
            "active_courses": courses_created, # Update this later when add an archived flag later
            "total_enrolled": total_enrolled,
            "total_students": total_students,
            "total_materials": total_materials,
            "category_choices": Course.CATEGORY_CHOICES, # For the create modal,
            "teacher_avg_rating": rating_data['global_avg'] or 0.0,
            "teacher_review_count": rating_data['total_reviews'],
        }

    return my_courses, stats