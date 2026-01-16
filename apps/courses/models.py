# apps/courses/models.py
from django.db import models
from django.conf import settings

class Course(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    # Teacher who owns the course
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="courses_taught",
        limit_choices_to={"role": "teacher"},
    )

    # Students enrolled in the course
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="courses_enrolled",
        blank=True,
        limit_choices_to={"role": "student"},
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class CourseFeedback(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="feedbacks",
    )
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "student"},
    )
    comment = models.TextField()
    rating = models.PositiveIntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.course.title} – {self.student.username}"
