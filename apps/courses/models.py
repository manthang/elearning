from django.db import models
from django.conf import settings

User = settings.AUTH_USER_MODEL


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Course(models.Model):
    course_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="courses"
    )

    def __str__(self):
        return f"{self.course_id} - {self.title}"


class Section(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="sections"
    )
    semester = models.CharField(max_length=20)
    year = models.IntegerField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["course", "semester", "year"],
                name="unique_course_section"
            )
        ]

    def __str__(self):
        return f"{self.course.course_id} ({self.semester} {self.year})"


class CourseFeedback(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "STUDENT"},
        related_name="feedbacks"
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="feedbacks"
    )
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "section"],
                name="unique_feedback_per_student_section"
            )
        ]

    def __str__(self):
        return f"Feedback by {self.student} for {self.section}"


class Teaching(models.Model):
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "TEACHER"},
        related_name="teaching_assignments"
    )
    section = models.ForeignKey(
        "Section",
        on_delete=models.CASCADE,
        related_name="teachers"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["teacher", "section"],
                name="unique_teaching"
            )
        ]

    def __str__(self):
        return f"{self.teacher} teaches {self.section}"


class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "STUDENT"},
        related_name="enrollments"
    )
    section = models.ForeignKey(
        "Section",
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    progress = models.PositiveIntegerField(default=0)
    grade = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["student", "section"],
                name="unique_enrollment"
            )
        ]
