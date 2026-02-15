from datetime import timedelta
from django.db import models
from django.conf import settings
from django.utils import timezone

User = settings.AUTH_USER_MODEL


# =========================
# Course
# =========================
class Course(models.Model):

    CATEGORY_WEB = "WEB"
    CATEGORY_DS = "DS"
    CATEGORY_ML = "ML"
    CATEGORY_DESIGN = "DESIGN"
    CATEGORY_GENERAL = "GENERAL"

    CATEGORY_CHOICES = [
        (CATEGORY_WEB, "Web Development"),
        (CATEGORY_DS, "Data Structures"),
        (CATEGORY_ML, "Machine Learning"),
        (CATEGORY_DESIGN, "Design"),
        (CATEGORY_GENERAL, "General"),
    ]

    course_id = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    category = models.CharField(
        max_length=30,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_GENERAL,
    )

    duration = models.CharField(
        max_length=50,
        blank=True,
        help_text="e.g., 12 weeks"
    )

    max_students = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Optional enrollment cap"
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "title"]

    def __str__(self):
        return f"{self.course_id} - {self.title}"

    # Helper property for dashboard
    @property
    def student_count(self):
        return self.enrollments.count()

    @property
    def is_full(self):
        if self.max_students:
            return self.student_count >= self.max_students
        return False


# =========================
# Course Materials
# =========================
class CourseMaterial(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="materials"
    )
    file = models.FileField(upload_to="course_materials/%Y/%m/%d/")
    original_name = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_materials"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def save(self, *args, **kwargs):
        if self.file and not self.original_name:
            self.original_name = self.file.name.split("/")[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course.title} - {self.original_name}"


# =========================
# Teaching
# =========================
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


# =========================
# Enrollment
# =========================
class Enrollment(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={"role": "STUDENT"},
        related_name="enrollments"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="enrollments"
    )
    progress = models.PositiveIntegerField(default=0)
    grade = models.CharField(max_length=2, blank=True, null=True)

    class Meta:
        unique_together = ("student", "course")

    def __str__(self):
        return f"{self.student} enrolled in {self.course}"


# =========================
# Course Feedback
# =========================
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


# =========================
# Deadline
# =========================
class Deadline(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="deadlines"
    )

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    due_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["due_at"]

    def is_overdue(self):
        return self.due_at < timezone.now()

    def is_due_soon(self):
        now = timezone.now()
        return now <= self.due_at <= now + timedelta(hours=48)

    def status(self):
        if self.is_overdue():
            return "due"
        if self.is_due_soon():
            return "due_soon"
        return "upcoming"

    def __str__(self):
        return f"{self.course.title} – {self.title}"
