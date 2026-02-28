from django.db.models import Avg, Count
from .models import *

def get_course_feedback_data(course):
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
        'rating_stats': rating_stats,
    }
