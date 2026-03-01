from django.conf import settings
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
    def short_name(self):
        # Splits the full name at the first space and returns the first word
        if self.full_name:
            return self.full_name.split()[0]
        return self.username

    @property
    def avatar_url(self):
        # If they have a custom uploaded photo, use it.
        if self.profile_photo:
            return self.profile_photo.url
            
        # If full_name is an empty string, fallback to username
        raw_name = self.full_name or self.username
        
        # Format the string for a URL (replace spaces with plus signs)
        safe_name = raw_name.replace(" ", "+")
        
        # Return the beautifully formatted fallback
        return f"https://ui-avatars.com/api/?name={safe_name}&background=F3F4F6&color=4B5563&size=200&font-size=0.4"

    @property
    def is_student(self):
        return self.role == self.Role.STUDENT

    @property
    def is_teacher(self):
        return self.role == self.Role.TEACHER

    def __str__(self):
        return self.username
