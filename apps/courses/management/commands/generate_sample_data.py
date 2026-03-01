import random
from datetime import timedelta
from faker import Faker

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.files.base import ContentFile

# Adjust the import path if your app is named differently
from apps.courses.models import (
    Course, Teaching, Enrollment, 
    CourseMaterial, Deadline, CourseFeedback
)

User = get_user_model()

class Command(BaseCommand):
    help = 'Generates full sample data based on the exact Course schema.'

    @transaction.atomic
    def handle(self, *args, **kwargs):
        fake = Faker()
        
        self.stdout.write("Clearing old dummy data...")
        User.objects.filter(username__startswith="dummy_").delete()
        Course.objects.filter(course_id__startswith="DUMMY-").delete()

        # ==========================================
        # 1 & 2. CREATE USERS (Teachers & Students)
        # ==========================================
        self.stdout.write("Creating 5 Teachers and 10 Students...")
        teachers = []
        for i in range(5):
            teachers.append(User.objects.create_user(
                username=f"dummy_teacher_{i}",
                email=f"teacher{i}@example.com",
                password="password123",
                full_name=fake.name(),
                role="TEACHER" 
            ))

        students = []
        for i in range(10):
            students.append(User.objects.create_user(
                username=f"dummy_student_{i}",
                email=f"student{i}@example.com",
                password="password123",
                full_name=fake.name(),
                role="STUDENT"
            ))

        # ==========================================
        # 3. CREATE COURSES & MAP TEACHERS
        # ==========================================
        self.stdout.write("Creating 50 Courses...")
        
        # Injecting highly realistic titles for an e-learning platform
        realistic_courses = [
            ("Advanced Django Rest Framework Architecture", Course.CATEGORY_WEB),
            ("Building Scalable E-learning Platforms", Course.CATEGORY_WEB),
            ("Normalizing Datasets for Machine Learning", Course.CATEGORY_DS),
            ("Representing RGB Images with 3D Vectors", Course.CATEGORY_ML),
            ("Analyzing the Washington State EV Dataset", Course.CATEGORY_DS),
        ]

        courses = []
        for i in range(50):
            # Use a realistic course or generate a random one
            if i < len(realistic_courses):
                title, category = realistic_courses[i]
            else:
                title = fake.catch_phrase().title()
                category = random.choice([c[0] for c in Course.CATEGORY_CHOICES])

            course = Course.objects.create(
                course_id=f"DUMMY-{fake.unique.random_int(min=1000, max=9999)}",
                title=title,
                description=fake.paragraph(nb_sentences=5),
                category=category,
                duration=f"{random.randint(4, 16)} weeks",
                max_students=random.choice([None, 50, 100, 200])
            )
            courses.append(course)
            
            Teaching.objects.create(
                course=course, 
                teacher=random.choice(teachers)
            )

        # ==========================================
        # 4. ENROLL STUDENTS
        # ==========================================
        self.stdout.write("Enrolling Students & Simulating Progress...")
        for student in students:
            # random.sample guarantees we don't violate the unique_together constraint
            student_courses = random.sample(courses, random.randint(3, 8))
            for course in student_courses:
                Enrollment.objects.create(
                    student=student,
                    course=course,
                    progress=random.randint(0, 100),
                    grade=random.choice([None, 'A', 'B', 'C', 'P', 'F'])
                )

        # ==========================================
        # 5. CREATE COURSE MATERIALS
        # ==========================================
        self.stdout.write("Generating Course Materials...")
        for course in courses:
            uploader = course.teachings.first().teacher
            for _ in range(random.randint(2, 6)):
                material = CourseMaterial(
                    course=course,
                    original_name=f"{fake.word()}_cheatsheet.pdf",
                    uploaded_by=uploader
                )
                # Create a safe, dummy text file in the database
                dummy_content = ContentFile(b"Dummy file content.")
                material.file.save(f"dummy_{fake.random_int()}.txt", dummy_content, save=True)

        # ==========================================
        # 6. CREATE DEADLINES
        # ==========================================
        self.stdout.write("Generating Deadlines...")
        for course in courses:
            for _ in range(random.randint(1, 4)):
                Deadline.objects.create(
                    course=course,
                    title=f"Assignment: {fake.bs().title()}",
                    description=fake.paragraph(nb_sentences=2),
                    # Range from 5 days ago (overdue) to 30 days from now (upcoming)
                    due_at=timezone.now() + timedelta(days=random.randint(-5, 30))
                )

        # ==========================================
        # 7. CREATE COURSE FEEDBACK
        # ==========================================
        self.stdout.write("Generating Student Feedback...")
        for enrollment in Enrollment.objects.all():
            # 60% chance a student leaves feedback
            if random.random() > 0.4:
                CourseFeedback.objects.create(
                    course=enrollment.course,
                    student=enrollment.student,
                    rating=random.randint(3, 5),
                    comment=fake.paragraph(nb_sentences=2) if random.random() > 0.5 else ""
                )

        self.stdout.write(self.style.SUCCESS("Successfully generated all dummy data!"))