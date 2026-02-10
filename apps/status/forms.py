from django import forms
from .models import StatusUpdate


class StatusUpdateForm(forms.ModelForm):
    class Meta:
        model = StatusUpdate
        fields = ["content"]
        widgets = {
            "content": forms.Textarea(attrs={
                "rows": 3,
                "placeholder": "Share an update with your classmates...",
                "class": (
                    "w-full border rounded-xl p-3 "
                    "focus:outline-none focus:ring focus:ring-blue-200"
                )
            })
        }

    def clean_content(self):
        content = self.cleaned_data["content"].strip()
        if not content:
            raise forms.ValidationError("Status update cannot be empty.")
        return content
