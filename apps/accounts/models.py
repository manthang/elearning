from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        STUDENT = "STUDENT", "Student"
        TEACHER = "TEACHER", "Teacher"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT
    )

    full_name = models.CharField(
        max_length=150,
        blank=True
    )
    
    location = models.CharField(
        max_length=255,
        blank=True,
        null=True,
    )

    profile_photo = models.ImageField(
        upload_to="profile_photos/",
        null=True,
        blank=True
    )

    bio = models.TextField(blank=True)

    @property
    def avatar_url(self):
        if self.profile_photo:
            return self.profile_photo.url
        return "/static/img/default-avatar.svg"

    def is_student(self):
        return self.role == self.Role.STUDENT

    def is_teacher(self):
        return self.role == self.Role.TEACHER

    def __str__(self):
        return self.username
