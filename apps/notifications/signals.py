# notifications/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from apps.courses.models import *
from apps.notifications.models import *
from .services import notify


@receiver(post_save, sender=Enrollment)
def notify_teachers_on_enroll(sender, instance, created, **kwargs):
    if not created:
        return

    course = instance.course
    student = instance.student

    # adjust to your schema:
    # - if Course has M2M teachers: course.teachers.all()
    # - if single instructor: course.instructor
    teachers = getattr(course, "teachers", None)
    teacher_qs = teachers.all() if teachers is not None else []

    url = reverse("courses:course_detail", kwargs={"course_id": course.id})

    for teacher in teacher_qs:
        notify(
            recipient=teacher,
            actor=student,
            course=course,
            verb="enrolled",
            title="New enrollment",
            message=f"{student.full_name or student.username} enrolled in {course.title}.",
            url=url,
        )



@receiver(post_save, sender=CourseMaterial)
def notify_students_on_new_material(sender, instance, created, **kwargs):
    if not created:
        return

    course = instance.course
    uploader = getattr(instance, "uploaded_by", None)

    url = reverse("courses:course_detail", kwargs={"course_id": course.id})

    # all enrolled students
    student_ids = Enrollment.objects.filter(course=course).values_list("student_id", flat=True)

    # optional: don't notify uploader if uploader is a student (rare)
    if uploader:
        student_ids = student_ids.exclude(student_id=uploader.id)

    notifs = [
        Notification(
            recipient_id=sid,
            actor=uploader,
            course=course,
            verb="material_added",
            title="New material uploaded",
            message=f"New material was added to {course.title}.",
            url=url,
        )
        for sid in student_ids
    ]
    Notification.objects.bulk_create(notifs, batch_size=500)