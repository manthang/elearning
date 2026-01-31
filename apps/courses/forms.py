# courses/forms.py
from django import forms
from .models import *

class CourseFeedbackForm(forms.ModelForm):
    class Meta:
        model = CourseFeedback
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.HiddenInput(),
            "comment": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Share your thoughts about the course, instructor, or learning experience..."
            }),
        }
