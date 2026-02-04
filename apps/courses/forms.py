# courses/forms.py
from django import forms
from .models import *

class CourseFeedbackForm(forms.ModelForm):
    rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        required=True
    )
    class Meta:
        model = CourseFeedback
        fields = ["rating", "comment"]

