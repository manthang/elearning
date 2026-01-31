from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Course(models.Model):
    course_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.course_id} - {self.title}"


class Teaching(models.Model):
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "TEACHER"},
        related_name="teachings"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="teachings"
    )

    class Meta:
        unique_together = ("teacher", "course")

    def __str__(self):
        return f"{self.teacher} teaches {self.course}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "STUDENT"},
        related_name="enrollments"
    )
    course = models.ForeignKey(
        Course  ,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    progress = models.PositiveIntegerField(default=0)
    grade = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"


class CourseFeedback(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "STUDENT"},
        related_name="feedbacks"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="feedbacks"
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"Feedback by {self.student} for {self.course}"

