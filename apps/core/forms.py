from django import forms
from .models import StatusUpdate

class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = StatusUpdate
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Share an update…",
                    "class": (
                        "w-full resize-none rounded-xl border border-gray-200 "
                        "p-4 focus:outline-none focus:ring-2 focus:ring-blue-500"
                    ),
                }
            )
        }
