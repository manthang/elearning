import random
from faker import Faker
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from apps.courses.models import Course, Teaching, Enrollment

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates sample data: 5 Teachers, 10 Students, 50 Courses.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fake = Faker()
        
        self.stdout.write("Clearing old dummy data...")
        # Optional: Delete previous dummy users to avoid IntegrityErrors
        User.objects.filter(username__startswith="dummy_").delete()
        Course.objects.filter(course_id__startswith="DUMMY-").delete()

        # 1. Create 5 Teachers
        self.stdout.write("Creating 5 Teachers...")
        teachers = []
        for i in range(5):
            teacher = User.objects.create_user(
                username=f"dummy_teacher_{i}",
                email=f"teacher{i}@example.com",
                password="password123",
                # Assuming your model uses full_name and role based on previous templates
                full_name=fake.name(),
                role=User.Role.TEACHER 
            )
            teachers.append(teacher)

        # 2. Create 10 Students
        self.stdout.write("Creating 10 Students...")
        students = []
        for i in range(10):
            student = User.objects.create_user(
                username=f"dummy_student_{i}",
                email=f"student{i}@example.com",
                password="password123",
                full_name=fake.name(),
                role=User.Role.STUDENT
            )
            students.append(student)

        # 3. Create 50 Courses & Map Teachers
        self.stdout.write("Creating 50 Courses...")
        categories = [choice[0] for choice in Course.CATEGORY_CHOICES] if hasattr(Course, 'CATEGORY_CHOICES') else ['programming', 'design', 'business']
        
        courses = []
        for i in range(50):
            course = Course.objects.create(
                course_id=f"DUMMY-{fake.unique.random_int(min=1000, max=9999)}",
                title=fake.catch_phrase().title(),
                description=fake.paragraph(nb_sentences=4),
                category=random.choice(categories),
                duration=f"{random.randint(4, 16)} weeks",
                max_students=random.choice([None, 50, 100, 200])
            )
            courses.append(course)

            # Assign 1 random teacher to this course
            Teaching.objects.create(
                course=course,
                teacher=random.choice(teachers)
            )

        # 4. Create Random Enrollments
        self.stdout.write("Enrolling Students...")
        for student in students:
            # Each student enrolls in 3 to 8 random courses
            student_courses = random.sample(courses, random.randint(3, 8))
            for course in student_courses:
                # Based on your templates, enrollment might have progress or review ratings
                Enrollment.objects.create(
                    student=student,
                    course=course,
                    # progress=random.randint(0, 100) # Uncomment if you have this field
                )

        self.stdout.write(self.style.SUCCESS("Successfully generated 5 teachers, 10 students, and 50 courses!"))