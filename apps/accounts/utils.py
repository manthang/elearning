from django.db.models import Count, Sum
from apps.courses.models import *


def _get_teacher_profile_data(teacher, is_own_profile):
    """Fetches teacher courses, and optionally private stats if it's their own dashboard."""
    
    # 1. Base Query (Visible to everyone)
    my_courses = (
        Course.objects
        .filter(teachings__teacher=teacher)
        .annotate(
            students_total=Count("enrollments", distinct=True),
            materials_total=Count("materials", distinct=True),
        )
        .order_by("-updated_at", "-created_at", "title")
        .distinct()
    )

    stats = {}

    # 2. Heavy Math (Strictly private to the owner)
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
        
        total_materials = CourseMaterial.objects.filter(course__teachings__teacher=teacher).count()

        # Capacity logic
        capped_qs = my_courses.filter(max_students__isnull=False)
        capacity_total = capped_qs.aggregate(total=Sum("max_students"))["total"] or 0
        capped_enrolled = Enrollment.objects.filter(
            course__teachings__teacher=teacher, 
            course__max_students__isnull=False
        ).count()

        capacity_used_pct = None
        if capacity_total > 0:
            capacity_used_pct = round((capped_enrolled / capacity_total) * 100)

        stats = {
            "courses_created": courses_created,
            "active_courses": courses_created, # Update this later if you add an archived flag
            "total_enrolled": total_enrolled,
            "total_students": total_students,
            "total_materials": total_materials,
            "capacity_used_pct": capacity_used_pct,
            "category_choices": Course.CATEGORY_CHOICES, # For the create modal
        }

    return my_courses, stats