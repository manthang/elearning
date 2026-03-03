from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from apps.courses.models import Enrollment, CourseMaterial, Teaching
from .models import Notification


def broadcast_notification(user_id, notif_data):
    """Helper function to send WebSocket data to a specific user."""
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"user_{user_id}",
        {
            "type": "live_notification", # This tells the consumer which method to run
            "payload": notif_data
        }
    )

# ========================================================
# Notify ONLY Teachers on Student Enrollment
# ========================================================
@receiver(post_save, sender=Enrollment)
def notify_teacher_on_enrollment(sender, instance, created, **kwargs):
    if created:
        course = instance.course
        student = instance.student
        
        teachings = Teaching.objects.filter(course=course).select_related('teacher')
        
        for teaching in teachings:
            msg = f"<b>{student.full_name}</b> enrolled in <b>{course.title}</b>."
            link = f"/courses/{course.id or course.course_id}/?tab=students"
            
            # 1. Save to Database FIRST to generate the ID
            notif = Notification.objects.create(
                recipient=teaching.teacher, 
                notification_type='ENROLLMENT', 
                message=msg, 
                link=link
            )
            
            # 2. Broadcast with the exact ID and read status
            broadcast_notification(teaching.teacher.id, {
                "id": notif.id,
                "is_read": False,
                "message": msg,
                "link": link,
                "notification_type": "ENROLLMENT",
                "time_ago": "Just now"
            })


# ========================================================
# Notify Students when new material is added
# ========================================================
@receiver(post_save, sender=CourseMaterial)
def notify_students_new_material(sender, instance, created, **kwargs):
    if created:
        course = instance.course
        enrollments = course.enrollments.select_related('student').all()
        
        for enrollment in enrollments:
            msg = f"New material uploaded to <b>{course.title}</b>: <b>{instance.original_name}</b>"
            link = f"/courses/{course.id or course.course_id}/?tab=materials"
            
            # 1. Save to Database FIRST
            notif = Notification.objects.create(
                recipient=enrollment.student, 
                notification_type='MATERIAL', 
                message=msg, 
                link=link
            )
            
            # 2. Broadcast
            broadcast_notification(enrollment.student.id, {
                "id": notif.id,
                "is_read": False,
                "message": msg,
                "link": link,
                "notification_type": "MATERIAL",
                "time_ago": "Just now"
            })
